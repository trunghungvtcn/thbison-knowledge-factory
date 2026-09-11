from __future__ import annotations

import os
import uuid
from typing import Any

from app.authority import AuthorityStore, parse_ts
from app.clock import utc_now_iso
from app.errors import AdapterError
from app.flock import InterprocessLock
from app.hashutil import hash_without, payload_hash, sha256_utf8
from app.ledger import Ledger
from app.provenance import code_commit, native_status
from app.runtime_port import RuntimeRetryPort
from app.sanitize import assert_safe_url, preserve_citations, sanitize_html
from app.simulator import CmsSimulator
from app.validate import validate

CONTRACT_VERSION = "1.0.0"
CONTRACT_SHA256 = "fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8"
ALLOWED_DESTINATIONS = {"test-cms", "staging-cms"}
ALLOWED_PROJECTS = {"test-thbison"}
MOCK_PRINCIPAL = "mock-service"
MOCK_TOKEN = "Bearer test-service"


def CODE_COMMIT() -> str:
    return code_commit()


class CmsAdapter:
    def __init__(self, ledger_path: str, clock=None, runtime: RuntimeRetryPort | None = None):
        self.ledger = Ledger(ledger_path)
        self.sim = CmsSimulator(self.ledger)
        self.authority = AuthorityStore()
        self.clock = clock or utc_now_iso
        self.allow_live = os.environ.get("ALLOW_PRODUCTION", "false").lower() == "true"
        self.allow_staging = os.environ.get("STAGING_WRITE_ENABLED", "false").lower() == "true"
        self.allow_public = os.environ.get("ALLOW_PUBLIC_EFFECTS", "false").lower() == "true"
        self.app_mode = os.environ.get("APP_MODE", "MOCK")
        self.cms_base = os.environ.get("CMS_STAGING_BASE_URL", "")
        self.cms_token = os.environ.get("CMS_STAGING_TOKEN", "")
        self.probe_verified = False
        self.runtime = runtime or RuntimeRetryPort(max_attempts=1)
        self.crash_after_accept = os.environ.get("CMS_CRASH_AFTER_ACCEPT", "") == "1"
        self.retry_calls: list[str] = self.runtime.attempts

    def inspect_capabilities(self) -> dict:
        sim_caps = self.sim.inspect_capabilities()
        status = native_status(self.app_mode, self.cms_base, self.cms_token, self.probe_verified)
        notes = []
        if status == "MOCK":
            notes.append("Adapter executes CmsSimulator only; env URL/token does not imply verified native CMS")
        if status == "BLOCKED_MISSING_INPUT":
            notes.append("BLOCKED_MISSING_INPUT: no CMS staging URL/token in allowlist")
        if status == "CONFIGURED_UNVERIFIED":
            notes.append("Credentials present in env but probe not verified; not AVAILABLE")
        if sim_caps.get("schema_drift"):
            raise AdapterError("CAPABILITY_MISMATCH", "Read-only discovery reports schema drift")
        return {
            "contract_version": CONTRACT_VERSION,
            "service": "cms-adapter",
            "code_commit": code_commit(),
            "contract_sha256": CONTRACT_SHA256,
            "mode": self.app_mode,
            "enabled_operations": [
                "publication.dry_run",
                "publication.staging_draft",
                "publication.reconcile",
                "cms.inspect",
                "cms.rollback_own_test",
            ],
            "max_json_bytes": 2097152,
            "provider": sim_caps,
            "native_cms_status": status,
            "notes": notes,
            "status": "SIMULATED",
        }

    def ledger_key(self, project_id: str, destination_id: str, operation: str, idem_key: str) -> str:
        return f"{project_id}|{destination_id}|{operation}|{idem_key}"

    def external_key(self, req: dict) -> str:
        return f"{req['article_id']}:{req['article_revision']}:{req['content_sha256']}"

    def authenticate(self, token: str | None, project_id: str) -> dict:
        if not token:
            raise AdapterError("UNAUTHORIZED", "Missing Authorization")
        if token != MOCK_TOKEN:
            raise AdapterError("UNAUTHORIZED", "Forged or unknown authentication denied")
        if self.allow_live or self.app_mode != "MOCK":
            if self.allow_live:
                raise AdapterError("FORBIDDEN", "MOCK identity never production authentication")
        if project_id not in ALLOWED_PROJECTS:
            raise AdapterError("FORBIDDEN", "Cross-project denied")
        return {"principal_id": MOCK_PRINCIPAL, "project_id": "test-thbison", "can_publish": True}

    def _check_schedule(self, scheduled_at: str | None) -> None:
        if scheduled_at is None:
            return
        try:
            parse_ts(scheduled_at)
        except AdapterError:
            raise
        except Exception as exc:
            raise AdapterError("SCHEDULE_INVALID", "Invalid scheduled_at") from exc
        raise AdapterError("SCHEDULE_INVALID", "Planning date cannot auto-publish; VPS B owns timer")

    def _verify_payload_digests(self, req: dict, article: dict, approval: dict, evidence: dict) -> None:
        content = hash_without(article, "content_sha256")
        if content != article.get("content_sha256"):
            raise AdapterError("STALE_APPROVAL", "Article bytes do not match content_sha256")
        snap = hash_without(evidence, "snapshot_sha256")
        if snap != evidence.get("snapshot_sha256"):
            raise AdapterError("STALE_APPROVAL", "Evidence bytes do not match snapshot_sha256")
        for field, actual, expected in (
            ("content_sha256", content, req["content_sha256"]),
            ("content_sha256", content, approval["content_sha256"]),
            ("evidence_snapshot_sha256", snap, req["evidence_snapshot_sha256"]),
            ("evidence_snapshot_sha256", snap, approval["evidence_snapshot_sha256"]),
            ("evidence_snapshot_sha256", snap, article["evidence_snapshot_sha256"]),
        ):
            if actual != expected:
                raise AdapterError("STALE_APPROVAL", f"Canonical {field} mismatch")

    def _authorize(self, req: dict, now: str) -> tuple[dict, dict, dict]:
        validate("PublishRequest", req)
        if req["project_id"] not in ALLOWED_PROJECTS:
            raise AdapterError("PROJECT_MISMATCH", "Project not bound")
        if req["destination_id"] not in ALLOWED_DESTINATIONS:
            raise AdapterError("DESTINATION_DENIED", "Destination not allowlisted")
        if req["mode"] == "LIVE" or req["data_class"] == "PRODUCTION":
            raise AdapterError("LIVE_DISABLED", "LIVE and PRODUCTION denied by default")
        if req["mode"] == "STAGING_DRAFT":
            if not self.allow_staging:
                raise AdapterError("STAGING_DISABLED", "STAGING_DRAFT requires STAGING_WRITE_ENABLED")
            if req["data_class"] != "STAGING":
                raise AdapterError("STAGING_DISABLED", "STAGING_DRAFT requires STAGING data_class")
        self._check_schedule(req.get("scheduled_at"))

        approval = self.authority.get_approval(req["approval_id"])
        article = self.authority.get_article(req["article_id"], req["article_revision"])
        evidence = self.authority.get_evidence(req["evidence_snapshot_sha256"])
        validate("ApprovalRecord", approval)
        validate("ArticlePackage", article)
        validate("EvidenceBundle", evidence)

        if approval["project_id"] != req["project_id"] or article["project_id"] != req["project_id"]:
            raise AdapterError("PROJECT_MISMATCH", "Cross-project request/approval denied")
        if approval["destination_id"] != req["destination_id"]:
            raise AdapterError("DESTINATION_DENIED", "Approval destination mismatch")
        for field in ("article_id", "article_revision", "content_sha256", "evidence_snapshot_sha256"):
            if req[field] != approval[field] or article[field] != approval[field]:
                raise AdapterError("STALE_APPROVAL", f"Approval not bound to {field}")
        self._verify_payload_digests(req, article, approval, evidence)
        if (
            article["data_class"] != req["data_class"]
            or approval["data_class"] != req["data_class"]
            or evidence.get("data_class") != req["data_class"]
        ):
            raise AdapterError("DATA_CLASS_MISMATCH", "Request/article/approval/evidence data_class not bound")
        if evidence.get("project_id") != req["project_id"]:
            raise AdapterError("PROJECT_MISMATCH", "Evidence project mismatch")
        if article.get("bundle_id") != evidence.get("bundle_id"):
            raise AdapterError("STALE_APPROVAL", "Article bundle_id not bound to evidence")
        policy = article.get("policy_version")
        if not policy or approval.get("policy_version") != policy or evidence.get("policy_version") != policy:
            raise AdapterError(
                "POLICY_MISMATCH",
                "Approval/article/evidence policy_version not bound",
            )
        if approval["decision"] == "REVOKED":
            raise AdapterError("APPROVAL_REVOKED", "Revoked approval prevents new effect")
        if approval["decision"] != "APPROVED":
            raise AdapterError("APPROVAL_NOT_ACTIVE", "Approval not APPROVED")
        now_dt = parse_ts(now)
        if not (parse_ts(approval["approved_at"]) <= now_dt < parse_ts(approval["expires_at"])):
            raise AdapterError("APPROVAL_EXPIRED", "Expired approval prevents new effect")
        if evidence.get("claims"):
            for c in evidence["claims"]:
                if c.get("status") in ("HOLD", "QUARANTINE"):
                    raise AdapterError("SOURCE_REVOKED", "Revoked evidence prevents new effect")
        return article, approval, evidence

    def _sanitize_article(self, article: dict) -> str:
        parts = []
        for b in article["blocks"]:
            text = sanitize_html(b["text"])
            preserve_citations(b["text"], text)
            for url_token in _extract_urls(text):
                assert_safe_url(url_token)
            parts.append(text)
        return "\n".join(parts)

    def _require_run_id_for_mutation(self, req: dict, test_run_id: str | None) -> str:
        if req["mode"] == "DRY_RUN":
            return test_run_id or ""
        if not test_run_id:
            raise AdapterError("VALIDATION_ERROR", "test_run_id required before any CMS mutation")
        return test_run_id

    def publish(self, req: dict, idem_key: str, token: str | None, test_run_id: str | None = None) -> dict:
        now = self.clock()
        self.authenticate(token, req.get("project_id", ""))
        article, approval, evidence = self._authorize(req, now)
        body = self._sanitize_article(article)
        run_id = self._require_run_id_for_mutation(req, test_run_id)
        operation = "publish"
        key = self.ledger_key(req["project_id"], req["destination_id"], operation, idem_key)
        phash = payload_hash(req)

        with InterprocessLock(self.ledger.path):
            existing = self.ledger.get_idem(key)
            if existing:
                if existing["payload_hash"] != phash:
                    raise AdapterError("IDEMPOTENCY_CONFLICT", "Same key different canonical payload")
                return existing["receipt"]

            if req["mode"] == "DRY_RUN":
                receipt = self._receipt(req, now, status="DRY_RUN", provider_id=None, url=None, effects=0)
                self.ledger.put_idem(key, phash, receipt, now)
                return receipt

            ext = self.external_key(req)
            found = self.sim.lookup(req["project_id"], req["destination_id"], ext)
            if found:
                receipt = self._receipt(
                    req, now, status="PUBLISHED",
                    provider_id=found.provider_record_id,
                    url=f"https://staging.test.thbison.local/drafts/{found.provider_record_id}",
                    effects=0,
                )
                self.ledger.put_idem(key, phash, receipt, now)
                return receipt

            try:
                draft = self._dispatch_create({
                    "project_id": req["project_id"],
                    "destination_id": req["destination_id"],
                    "external_key": ext,
                    "article_id": req["article_id"],
                    "article_revision": req["article_revision"],
                    "content_sha256": req["content_sha256"],
                    "body": body,
                    "test_run_id": run_id,
                    "created_at": now,
                })
            except AdapterError as err:
                if err.code == "TIMEOUT":
                    looked = self.sim.lookup(req["project_id"], req["destination_id"], ext)
                    pub_id = "pub-" + sha256_utf8(key)[:16]
                    if looked:
                        self._persist_owned_draft(looked, req, ext, run_id, now)
                        receipt = self._receipt(
                            req, now, status="UNKNOWN",
                            provider_id=looked.provider_record_id, url=None, effects=1,
                            publication_id=pub_id,
                        )
                    else:
                        receipt = self._receipt(
                            req, now, status="UNKNOWN", provider_id=None, url=None, effects=0,
                            publication_id=pub_id,
                        )
                    self.ledger.put_unknown(pub_id, key, 1, "UNKNOWN")
                    self.ledger.put_idem(key, phash, receipt, now)
                    raise AdapterError("TIMEOUT", err.message, True) from err
                raise

            if draft.public and not self.allow_public:
                raise AdapterError("FORBIDDEN", "Public effects denied")

            self._persist_owned_draft(draft, req, ext, run_id, now)
            if self.crash_after_accept:
                os._exit(99)
            receipt = self._receipt(
                req, now, status="PUBLISHED",
                provider_id=draft.provider_record_id,
                url=f"https://staging.test.thbison.local/drafts/{draft.provider_record_id}",
                effects=1,
            )
            self.ledger.put_idem(key, phash, receipt, now)
            return receipt

    def _persist_owned_draft(self, draft, req, ext, run_id, now) -> None:
        self.ledger.put_draft({
            "provider_record_id": draft.provider_record_id,
            "project_id": req["project_id"],
            "destination_id": req["destination_id"],
            "external_key": ext,
            "article_id": req["article_id"],
            "article_revision": req["article_revision"],
            "content_sha256": req["content_sha256"],
            "revision": draft.revision,
            "body": draft.body,
            "public": False,
            "test_run_id": run_id,
            "created_at": now,
        })
        self.ledger.record_mutation({
            "mutation_id": "mut-" + uuid.uuid4().hex[:12],
            "test_run_id": run_id,
            "provider_record_id": draft.provider_record_id,
            "action": "createDraft",
            "before": None,
            "after": {"provider_record_id": draft.provider_record_id},
        })

    def _dispatch_create(self, inp: dict):
        def _once():
            return self.sim.create_draft(inp)
        return self.runtime.run(_once)

    def reconcile(self, publication_id: str) -> dict:
        unk = self.ledger.get_unknown(publication_id)
        if not unk:
            raise AdapterError("VALIDATION_ERROR", "No UNKNOWN outcome for publication")
        if unk["attempts"] >= 5:
            raise AdapterError("PUBLICATION_UNKNOWN", "Bounded reconciliation exhausted")
        self.ledger.put_unknown(publication_id, unk["ledger_key"], unk["attempts"] + 1, "RECONCILING")
        return {"publication_id": publication_id, "attempts": unk["attempts"] + 1, "status": "RECONCILING"}

    def update_draft(self, provider_record_id: str, expected_revision: int, body: str, content_sha256: str):
        sanitize_html(body)
        return self.sim.update(provider_record_id, expected_revision, body, content_sha256)

    def rollback_own(self, test_run_id: str) -> dict:
        if not test_run_id:
            raise AdapterError("VALIDATION_ERROR", "test_run_id required")
        rows = self.ledger.list_by_run(test_run_id)
        removed = []
        for d in rows:
            self.sim.delete(d["provider_record_id"])
            self.ledger.delete_draft(d["provider_record_id"])
            removed.append(d["provider_record_id"])
        return {"rolled_back": removed, "count": len(removed)}

    def _receipt(self, req, now, status, provider_id, url, effects, publication_id=None):
        pub = publication_id or ("pub-" + sha256_utf8(req["request_id"] + req["content_sha256"])[:16])
        rec = {
            "contract_version": CONTRACT_VERSION,
            "project_id": req["project_id"],
            "data_class": req["data_class"],
            "publication_id": pub,
            "request_id": req["request_id"],
            "article_id": req["article_id"],
            "article_revision": req["article_revision"],
            "destination_id": req["destination_id"],
            "content_sha256": req["content_sha256"],
            "status": status,
            "provider_record_id": provider_id,
            "provider_url": url,
            "created_at": now,
            "actual_side_effects": effects,
        }
        validate("PublicationReceipt", rec)
        rec["_source_revision"] = code_commit()
        rec["_contract_sha256"] = CONTRACT_SHA256
        rec["_payload_sha256"] = payload_hash({k: v for k, v in rec.items() if not k.startswith("_")})
        return rec


def _extract_urls(text: str) -> list[str]:
    out = []
    for token in text.split():
        if token.startswith("http://") or token.startswith("https://"):
            out.append(token.rstrip(".,)"))
    return out
