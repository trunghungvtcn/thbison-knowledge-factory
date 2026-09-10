"""Job state machine, lease, budget, idempotency, audit."""
from __future__ import annotations

import hashlib
import os
import re
import uuid
from typing import Any

from . import CODE_COMMIT, CONTRACT_SHA256, CONTRACT_VERSION
from .projection import project_receipt_status
from .store import Store, dumps

TERMINAL = {"SUCCEEDED", "FAILED", "CANCELLED", "BLOCKED_INPUT"}
INTERNAL_STATES = {"QUEUED", "LEASED", "RUNNING", "SUCCEEDED", "FAILED", "CANCELLED", "BLOCKED_INPUT"}
# Public mapping lives in app.projection (OWNER DECISION OPEN).
ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}$")
SECRET_RE = re.compile(r"(password|secret|token|api[_-]?key|authorization)", re.I)

NON_RETRYABLE = {"VALIDATION_ERROR", "UNAUTHORIZED", "FORBIDDEN", "UNSUPPORTED_CONTRACT", "IDEMPOTENCY_CONFLICT"}


def canonical_hash(payload: dict) -> str:
    raw = dumps({k: payload[k] for k in sorted(payload) if k != "trace_id"})
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def new_id(prefix: str = "j") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:16]}"


def redact(obj: Any) -> Any:
    if isinstance(obj, dict):
        out = {}
        for k, v in obj.items():
            if SECRET_RE.search(str(k)):
                out[k] = "[REDACTED]"
            else:
                out[k] = redact(v)
        return out
    if isinstance(obj, list):
        return [redact(x) for x in obj]
    if isinstance(obj, str) and SECRET_RE.search(obj) and len(obj) > 12:
        return "[REDACTED]"
    return obj


class Runtime:
    def __init__(self, store: Store, egress_blocked: bool = True) -> None:
        self.store = store
        self.egress_blocked = egress_blocked
        self.allow_production = os.getenv("ALLOW_PRODUCTION", "false").lower() == "true"
        self.allow_public = os.getenv("ALLOW_PUBLIC_EFFECTS", "false").lower() == "true"
        self.mode = os.getenv("APP_MODE", "MOCK")
        self._append_audit(None, None, "RUNTIME_START", {"mode": self.mode})

    def _append_audit(self, job_id: str | None, project_id: str | None, event_type: str, payload: dict) -> None:
        last = self.store.fetchone("SELECT event_hash FROM audit ORDER BY seq DESC LIMIT 1")
        prev = last["event_hash"] if last else "0" * 64
        body = dumps(redact(payload))
        event_id = new_id("ev")
        material = f"{prev}|{event_id}|{event_type}|{body}"
        eh = hashlib.sha256(material.encode("utf-8")).hexdigest()
        self.store.execute(
            "INSERT INTO audit(event_id, job_id, project_id, event_type, payload, prev_hash, event_hash, created_at) VALUES(?,?,?,?,?,?,?,?)",
            (event_id, job_id, project_id, event_type, body, prev, eh, self.store.now()),
        )

    def audit_chain_valid(self) -> bool:
        rows = self.store.fetchall("SELECT * FROM audit ORDER BY seq ASC")
        prev = "0" * 64
        for r in rows:
            material = f"{prev}|{r['event_id']}|{r['event_type']}|{r['payload']}"
            if hashlib.sha256(material.encode("utf-8")).hexdigest() != r["event_hash"]:
                return False
            if r["prev_hash"] != prev:
                return False
            prev = r["event_hash"]
        return True

    def submit_job(
        self,
        *,
        project_id: str,
        operation: str,
        idempotency_key: str,
        request_id: str,
        data_class: str,
        payload: dict,
        budget: dict | None,
        extra_fields: bool = False,
    ) -> tuple[int, dict]:
        if extra_fields:
            return 400, self._err(request_id, "VALIDATION_ERROR", "additional properties not allowed", False)
        if data_class == "PRODUCTION" and not self.allow_production:
            return 403, self._err(request_id, "FORBIDDEN", "production data class denied", False)
        if not ID_RE.match(project_id or "") or not ID_RE.match(idempotency_key or "") or not ID_RE.match(request_id or ""):
            return 400, self._err(request_id or "invalid", "VALIDATION_ERROR", "invalid identifier", False)
        if operation not in {"plan", "draft", "evidence", "approve", "publish"}:
            return 400, self._err(request_id, "VALIDATION_ERROR", "unsupported operation", False)

        req_hash = canonical_hash({"project_id": project_id, "operation": operation, "payload": payload, "data_class": data_class})
        existing = self.store.fetchone(
            "SELECT * FROM jobs WHERE project_id=? AND operation=? AND idempotency_key=?",
            (project_id, operation, idempotency_key),
        )
        if existing:
            if existing["request_hash"] != req_hash:
                return 409, self._err(request_id, "IDEMPOTENCY_CONFLICT", "same key different hash", False)
            return 202, self._receipt(existing)

        job_id = new_id("job")
        now = self.store.now()
        max_attempts = 3
        max_req = int((budget or {}).get("max_requests", 4))
        max_cost = float((budget or {}).get("max_cost_units", 20))
        deadline = now + 3600
        with self.store.tx() as conn:
            conn.execute(
                """INSERT INTO jobs(job_id,project_id,operation,idempotency_key,request_hash,request_id,data_class,status,attempt,max_attempts,payload,error_code,result_artifact,created_at,updated_at,deadline_at,cancelled)
                   VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                (job_id, project_id, operation, idempotency_key, req_hash, request_id, data_class, "QUEUED", 0, max_attempts, dumps(payload), None, None, now, now, deadline, 0),
            )
            conn.execute(
                "INSERT INTO budgets(job_id,max_requests,max_cost_units) VALUES(?,?,?)",
                (job_id, max_req, max_cost),
            )
        job = self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        self._append_audit(job_id, project_id, "JOB_SUBMITTED", {"job_id": job_id, "operation": operation})
        return 202, self._receipt(job)

    def get_job(self, job_id: str, project_id: str) -> tuple[int, dict]:
        job = self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        if not job:
            return 404, self._err("na", "VALIDATION_ERROR", "job not found", False)
        if job["project_id"] != project_id:
            return 403, self._err(job["request_id"], "FORBIDDEN", "cross-project denied", False)
        return 200, self._receipt(job)

    def cancel(self, job_id: str, project_id: str) -> tuple[int, dict]:
        job = self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        if not job:
            return 404, self._err("na", "VALIDATION_ERROR", "job not found", False)
        if job["project_id"] != project_id:
            return 403, self._err(job["request_id"], "FORBIDDEN", "cross-project denied", False)
        if job["status"] in TERMINAL:
            return 200, self._receipt(job)
        self.store.execute(
            "UPDATE jobs SET status='CANCELLED', cancelled=1, updated_at=? WHERE job_id=?",
            (self.store.now(), job_id),
        )
        self._append_audit(job_id, project_id, "JOB_CANCELLED", {"job_id": job_id, "from": job["status"]})
        job = self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        return 200, self._receipt(job)

    def claim(self, *, project_id: str, worker_id: str, request_id: str) -> tuple[int, dict]:
        now = self.store.now()
        self._expire_leases(now)
        with self.store.tx() as conn:
            row = conn.execute(
                "SELECT * FROM jobs WHERE project_id=? AND status='QUEUED' AND cancelled=0 ORDER BY created_at LIMIT 1",
                (project_id,),
            ).fetchone()
            if not row:
                return 204, {}
            job = dict(row)
            if job["attempt"] >= job["max_attempts"]:
                conn.execute(
                    "UPDATE jobs SET status='FAILED', error_code='BUDGET_EXHAUSTED', updated_at=? WHERE job_id=?",
                    (now, job["job_id"]),
                )
                return 204, {}
            budget = dict(conn.execute("SELECT * FROM budgets WHERE job_id=?", (job["job_id"],)).fetchone())
            if budget["consumed_requests"] + budget["reserved_requests"] >= budget["max_requests"]:
                conn.execute(
                    "UPDATE jobs SET status='FAILED', error_code='BUDGET_EXHAUSTED', updated_at=? WHERE job_id=?",
                    (now, job["job_id"]),
                )
                return 204, {}
            attempt = job["attempt"] + 1
            lease_id = new_id("lease")
            expires = now + 30
            conn.execute(
                "UPDATE jobs SET status='LEASED', attempt=?, updated_at=? WHERE job_id=?",
                (attempt, now, job["job_id"]),
            )
            conn.execute(
                "INSERT INTO leases(lease_id,job_id,project_id,worker_id,attempt,expires_at,status,created_at) VALUES(?,?,?,?,?,?,?,?)",
                (lease_id, job["job_id"], project_id, worker_id, attempt, expires, "ACTIVE", now),
            )
            conn.execute(
                "UPDATE budgets SET reserved_requests=reserved_requests+1 WHERE job_id=?",
                (job["job_id"],),
            )
        self._append_audit(job["job_id"], project_id, "LEASE_CLAIMED", {"lease_id": lease_id, "attempt": attempt, "worker_id": worker_id})
        return 200, {
            "lease_id": lease_id,
            "job_id": job["job_id"],
            "project_id": project_id,
            "attempt": attempt,
            "expires_at": expires,
            "worker_id": worker_id,
            "operation": job["operation"],
            "payload": job["payload"],
        }

    def heartbeat(self, lease_id: str, project_id: str, worker_id: str) -> tuple[int, dict]:
        now = self.store.now()
        lease = self.store.fetchone("SELECT * FROM leases WHERE lease_id=?", (lease_id,))
        if not lease:
            return 404, self._err("na", "VALIDATION_ERROR", "lease not found", False)
        if lease["project_id"] != project_id or lease["worker_id"] != worker_id:
            return 403, self._err("na", "FORBIDDEN", "lease identity mismatch", False)
        if lease["status"] != "ACTIVE" or lease["expires_at"] < now:
            return 409, self._err("na", "TIMEOUT", "lease expired", True)
        new_exp = now + 30
        self.store.execute("UPDATE leases SET expires_at=? WHERE lease_id=?", (new_exp, lease_id))
        job = self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (lease["job_id"],))
        if job and job["status"] == "LEASED":
            self.store.execute("UPDATE jobs SET status='RUNNING', updated_at=? WHERE job_id=?", (now, lease["job_id"]))
        return 200, {"lease_id": lease_id, "expires_at": new_exp}

    def complete(
        self,
        lease_id: str,
        project_id: str,
        worker_id: str,
        *,
        success: bool,
        retryable: bool = False,
        error_code: str | None = None,
        artifact: dict | None = None,
        unknown: bool = False,
    ) -> tuple[int, dict]:
        now = self.store.now()
        lease = self.store.fetchone("SELECT * FROM leases WHERE lease_id=?", (lease_id,))
        if not lease:
            return 404, self._err("na", "VALIDATION_ERROR", "lease not found", False)
        if lease["project_id"] != project_id or lease["worker_id"] != worker_id:
            return 403, self._err("na", "FORBIDDEN", "lease identity mismatch", False)
        job = self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (lease["job_id"],))
        if not job:
            return 404, self._err("na", "VALIDATION_ERROR", "job missing", False)
        if job["status"] in TERMINAL:
            existing = self.store.fetchone(
                "SELECT * FROM receipts WHERE job_id=? AND kind='completion' ORDER BY created_at DESC LIMIT 1",
                (job["job_id"],),
            )
            if existing:
                return 200, json_loads(existing["payload"])
            return 409, self._err(job["request_id"], "STALE_REVISION", "job already terminal", False)
        if lease["status"] != "ACTIVE" or lease["expires_at"] < now:
            return 409, self._err(job["request_id"], "TIMEOUT", "complete after expiry rejected", True)
        if lease["attempt"] != job["attempt"]:
            return 409, self._err(job["request_id"], "STALE_REVISION", "attempt mismatch", False)

        if unknown:
            oid = new_id("unk")
            self.store.execute(
                "INSERT INTO unknown_outcomes(outcome_id,job_id,provider,lookup_key,status,created_at) VALUES(?,?,?,?,?,?)",
                (oid, job["job_id"], worker_id, lease_id, "UNKNOWN", now),
            )
            self.store.execute(
                "UPDATE budgets SET reserved_requests=MAX(reserved_requests-1,0), consumed_requests=consumed_requests+1 WHERE job_id=?",
                (job["job_id"],),
            )
            self.store.execute("UPDATE leases SET status='UNKNOWN' WHERE lease_id=?", (lease_id,))
            self._append_audit(job["job_id"], project_id, "RESULT_UNKNOWN", {"lease_id": lease_id})
            return 202, {"status": "UNKNOWN", "job_id": job["job_id"], "outcome_id": oid}

        if success:
            new_status = "SUCCEEDED"
            err = None
            art = dumps(artifact) if artifact else None
        else:
            if retryable and job["attempt"] < job["max_attempts"] and error_code not in NON_RETRYABLE:
                new_status = "QUEUED"
                err = error_code or "PROVIDER_ERROR"
                art = None
            else:
                new_status = "FAILED"
                err = error_code or "PROVIDER_ERROR"
                art = None

        self.store.execute(
            "UPDATE jobs SET status=?, error_code=?, result_artifact=?, updated_at=? WHERE job_id=?",
            (new_status, err, art, now, job["job_id"]),
        )
        self.store.execute("UPDATE leases SET status='COMPLETED' WHERE lease_id=?", (lease_id,))
        self.store.execute(
            "UPDATE budgets SET reserved_requests=MAX(reserved_requests-1,0), consumed_requests=consumed_requests+1 WHERE job_id=?",
            (job["job_id"],),
        )
        receipt = self._receipt(self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (job["job_id"],)))
        rid = new_id("rcpt")
        self.store.execute(
            "INSERT INTO receipts(receipt_id,job_id,project_id,kind,provider_ref,payload,created_at) VALUES(?,?,?,?,?,?,?)",
            (rid, job["job_id"], project_id, "completion", lease_id, dumps(receipt), now),
        )
        self._append_audit(job["job_id"], project_id, "JOB_COMPLETED", {"status": new_status, "lease_id": lease_id})
        return 200, receipt

    def reconcile(self, job_id: str, project_id: str) -> tuple[int, dict]:
        job = self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        if not job:
            return 404, self._err("na", "VALIDATION_ERROR", "job not found", False)
        if job["project_id"] != project_id:
            return 403, self._err(job["request_id"], "FORBIDDEN", "cross-project denied", False)
        unk = self.store.fetchall("SELECT * FROM unknown_outcomes WHERE job_id=? AND status='UNKNOWN'", (job_id,))
        if not unk:
            return 200, {"reconciled": 0, "job": self._receipt(job)}
        # Lookup simulator: treat provider_ref as found receipt without new side effect
        now = self.store.now()
        for u in unk:
            self.store.execute("UPDATE unknown_outcomes SET status='RECONCILED' WHERE outcome_id=?", (u["outcome_id"],))
            existing_receipt = self.store.fetchone(
                "SELECT * FROM receipts WHERE job_id=? AND kind='completion'",
                (job_id,),
            )
            if existing_receipt:
                continue
            if job["status"] not in TERMINAL:
                self.store.execute(
                    "UPDATE jobs SET status='SUCCEEDED', updated_at=? WHERE job_id=?",
                    (now, job_id),
                )
                rec = self._receipt(self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (job_id,)))
                self.store.execute(
                    "INSERT INTO receipts(receipt_id,job_id,project_id,kind,provider_ref,payload,created_at) VALUES(?,?,?,?,?,?,?)",
                    (new_id("rcpt"), job_id, project_id, "completion", u["lookup_key"], dumps(rec), now),
                )
        self._append_audit(job_id, project_id, "RECONCILED", {"count": len(unk)})
        job = self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (job_id,))
        return 200, {"reconciled": len(unk), "job": self._receipt(job), "blind_retry": False}

    def block_module_schedule(self, module: str) -> tuple[int, dict]:
        row = self.store.fetchone("SELECT * FROM module_schedule_blocks WHERE module=?", (module,))
        if row and row["blocked"]:
            return 403, self._err("na", "FORBIDDEN", "modules must not create their own scheduler", False)
        return 400, self._err("na", "VALIDATION_ERROR", "unknown module", False)

    def reserve_budget(self, job_id: str, requests: int, cost: float) -> bool:
        with self.store.tx() as conn:
            b = conn.execute("SELECT * FROM budgets WHERE job_id=?", (job_id,)).fetchone()
            if not b:
                return False
            b = dict(b)
            if b["reserved_requests"] + b["consumed_requests"] + requests > b["max_requests"]:
                return False
            if b["reserved_cost"] + b["consumed_cost"] + cost > b["max_cost_units"]:
                return False
            conn.execute(
                "UPDATE budgets SET reserved_requests=reserved_requests+?, reserved_cost=reserved_cost+? WHERE job_id=?",
                (requests, cost, job_id),
            )
            return True

    def deny_production(self) -> tuple[int, dict]:
        return 403, self._err("na", "FORBIDDEN", "production endpoint/credential denied", False)

    def _expire_leases(self, now: float) -> None:
        rows = self.store.fetchall("SELECT * FROM leases WHERE status='ACTIVE' AND expires_at<?", (now,))
        for lease in rows:
            self.store.execute("UPDATE leases SET status='EXPIRED' WHERE lease_id=?", (lease["lease_id"],))
            job = self.store.fetchone("SELECT * FROM jobs WHERE job_id=?", (lease["job_id"],))
            if not job or job["status"] in TERMINAL:
                continue
            if job["cancelled"]:
                self.store.execute("UPDATE jobs SET status='CANCELLED', updated_at=? WHERE job_id=?", (now, job["job_id"]))
            elif job["attempt"] >= job["max_attempts"]:
                self.store.execute(
                    "UPDATE jobs SET status='FAILED', error_code='BUDGET_EXHAUSTED', updated_at=? WHERE job_id=?",
                    (now, job["job_id"]),
                )
            else:
                self.store.execute("UPDATE jobs SET status='QUEUED', updated_at=? WHERE job_id=?", (now, job["job_id"]))
            self.store.execute(
                "UPDATE budgets SET reserved_requests=MAX(reserved_requests-1,0) WHERE job_id=?",
                (job["job_id"],),
            )

    def expire_now(self) -> None:
        self._expire_leases(self.store.now())

    def _receipt(self, job: dict) -> dict:
        art = None
        if job.get("result_artifact"):
            art = json_loads(job["result_artifact"])
        public = project_receipt_status(job["status"], job.get("error_code"))
        return {
            "contract_version": CONTRACT_VERSION,
            "project_id": job["project_id"],
            "data_class": job["data_class"],
            "job_id": job["job_id"],
            "request_id": job["request_id"],
            "status": public,
            "code_commit": CODE_COMMIT,
            "contract_sha256": CONTRACT_SHA256,
            "result_artifact": art,
            "error_code": job.get("error_code"),
        }

    def _err(self, request_id: str, code: str, message: str, retryable: bool) -> dict:
        return {
            "contract_version": CONTRACT_VERSION,
            "request_id": request_id if ID_RE.match(request_id or "") else "invalid-request",
            "code": code,
            "message": message,
            "retryable": retryable,
        }


def json_loads(s: str) -> Any:
    import json
    return json.loads(s)
