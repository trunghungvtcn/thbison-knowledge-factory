"""Vendor 3 runtime/orchestrator subset: jobs, idempotency, budget, leases."""

from __future__ import annotations

from typing import Any

from thbison_v6.faults import FaultPlan
from thbison_v6.hashutil import payload_digest
from thbison_v6.ledger import Clock, FileLedger


class RuntimeSimulator:
    vendor = "VENDOR_3"
    kind = "STUB"

    def __init__(
        self,
        ledger: FileLedger,
        clock: Clock,
        faults: FaultPlan | None = None,
        budget_cap: int = 5,
    ):
        self.ledger = ledger
        self.clock = clock
        self.faults = faults or FaultPlan()
        self.budget_cap = budget_cap

    def admit(self, project_id: str, op: str, idem_key: str, payload: dict[str, Any]) -> dict[str, Any]:
        key = f"{project_id}:{op}:{idem_key}"
        digest = payload_digest(payload)
        existing = self.ledger.get("jobs", key)
        if existing:
            if existing.get("payload_digest") != digest:
                raise ValueError("IDEMPOTENCY_CONFLICT")
            return existing
        with self.ledger._lock:
            spent = int(self.ledger.get("budget", project_id, 0) or 0)
            if spent >= self.budget_cap:
                raise PermissionError("BUDGET_EXCEEDED")
            job = {
                "job_id": key,
                "project_id": project_id,
                "op": op,
                "idempotency_key": idem_key,
                "payload_digest": digest,
                "status": "RUNNING",
                "attempt": 1,
                "lease_expires_at": self.clock.now() + 30,
                "cancelled": False,
                "created_at": self.clock.now(),
            }
            jobs = self.ledger.get_map("jobs")
            jobs[key] = job
            self.ledger.save("jobs", jobs)
            budgets = self.ledger.get_map("budget")
            budgets[project_id] = spent + 1
            self.ledger.save("budget", budgets)
        return job

    def complete(self, job_id: str, result: dict[str, Any], attempt: int | None = None) -> dict[str, Any]:
        job = dict(self.ledger.get("jobs", job_id))
        if job.get("cancelled"):
            raise PermissionError("STALE_COMPLETION_REJECTED")
        if job.get("lease_expires_at", 0) <= self.clock.now():
            raise PermissionError("EXPIRED_LEASE")
        if attempt is not None and attempt < job.get("attempt", 1):
            raise PermissionError("STALE_ATTEMPT")
        job["status"] = "SUCCEEDED"
        job["result"] = result
        self.ledger.put("jobs", job_id, job)
        return job

    def cancel(self, job_id: str) -> dict[str, Any]:
        job = dict(self.ledger.get("jobs", job_id))
        job["cancelled"] = True
        job["status"] = "CANCELLED"
        self.ledger.put("jobs", job_id, job)
        return job

    def bump_attempt(self, job_id: str) -> dict[str, Any]:
        job = dict(self.ledger.get("jobs", job_id))
        job["attempt"] = int(job.get("attempt", 1)) + 1
        job["lease_expires_at"] = self.clock.now() + 30
        self.ledger.put("jobs", job_id, job)
        return job

    def reconcile_unknown(self, job_id: str, loops: int = 0) -> str:
        if loops > 2:
            return "BOUNDED_STOP"
        job = self.ledger.get("jobs", job_id)
        if not job:
            return "MISSING"
        if job.get("status") == "SUCCEEDED":
            return "ALREADY_DONE"
        return "RETRY_ONCE"
