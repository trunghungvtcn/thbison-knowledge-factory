"""Vendor 5 CMS adapter simulator. Actual V5 is MISSING."""

from __future__ import annotations

from typing import Any

from thbison_v6.contract_validate import assert_valid
from thbison_v6.faults import FaultPlan
from thbison_v6.hashutil import payload_digest
from thbison_v6.ledger import Clock, FileLedger
from thbison_v6.timefmt import iso_z


class CmsSimulator:
    vendor = "VENDOR_5"
    kind = "STUB"

    def __init__(self, ledger: FileLedger, clock: Clock | None = None, faults: FaultPlan | None = None):
        self.ledger = ledger
        self.clock = clock or Clock()
        self.faults = faults or FaultPlan()

    def publish(self, req: dict[str, Any], approval: dict[str, Any] | None) -> dict[str, Any]:
        mode = req.get("mode", "DRY_RUN")
        if mode == "LIVE":
            raise PermissionError("LIVE_DENIED")
        if mode != "DRY_RUN":
            if not approval or approval.get("decision") != "APPROVED":
                raise PermissionError("APPROVAL_REQUIRED")
            if approval.get("content_sha256") != req.get("content_sha256"):
                raise PermissionError("APPROVAL_MISMATCH")
            if approval.get("destination_id") != req.get("destination_id"):
                raise PermissionError("DESTINATION_MISMATCH")
            if approval.get("article_revision") != req.get("article_revision"):
                raise PermissionError("REVISION_MISMATCH")
            if approval.get("evidence_snapshot_sha256") != req.get("evidence_snapshot_sha256"):
                raise PermissionError("EVIDENCE_MISMATCH")
        if mode == "DRY_RUN":
            receipt = {
                "contract_version": "1.0.0",
                "project_id": req["project_id"],
                "data_class": "TEST_ONLY",
                "publication_id": "pub-dry-none",
                "request_id": req.get("request_id", "req-dry"),
                "article_id": req["article_id"],
                "article_revision": req["article_revision"],
                "destination_id": req["destination_id"],
                "content_sha256": req["content_sha256"],
                "status": "DRY_RUN",
                "provider_record_id": None,
                "provider_url": None,
                "created_at": iso_z(self.clock.now()),
                "actual_side_effects": 0,
            }
            assert_valid("PublicationReceipt", receipt)
            return receipt
        if self.faults.status_429:
            raise RuntimeError("HTTP_429")
        if self.faults.timeout:
            raise TimeoutError("CMS_TIMEOUT")
        if self.faults.unknown_after_accept:
            receipt = {
                "contract_version": "1.0.0",
                "project_id": req["project_id"],
                "data_class": "TEST_ONLY",
                "publication_id": "pub-unknown",
                "request_id": req.get("request_id", "req-unk"),
                "article_id": req["article_id"],
                "article_revision": req["article_revision"],
                "destination_id": req["destination_id"],
                "content_sha256": req["content_sha256"],
                "status": "UNKNOWN",
                "provider_record_id": None,
                "provider_url": None,
                "created_at": iso_z(self.clock.now()),
                "actual_side_effects": 0,
            }
            assert_valid("PublicationReceipt", receipt)
            return receipt

        key = f"{req.get('project_id')}:{req.get('destination_id')}:{req.get('request_id')}"
        existing = self.ledger.get("cms_effects", key)
        digest = payload_digest({k: req[k] for k in sorted(req) if k != "trace_id"})
        if existing:
            stored = {k: v for k, v in existing.items() if k != "payload_digest"}
            if existing.get("payload_digest") != digest:
                raise ValueError("IDEMPOTENCY_CONFLICT")
            return stored
        if self.faults.schema_drift:
            rec = {"weirdField": True, "not_a_receipt": 1}
            self.ledger.put("cms_effects", key, rec)
            return rec
        rec = {
            "contract_version": "1.0.0",
            "project_id": req["project_id"],
            "data_class": "TEST_ONLY",
            "publication_id": f"pub-{req.get('request_id', 'x')}",
            "request_id": req.get("request_id", "req-1"),
            "article_id": req["article_id"],
            "article_revision": req["article_revision"],
            "destination_id": req["destination_id"],
            "content_sha256": req["content_sha256"],
            "status": "SCHEDULED",
            "provider_record_id": f"cms-{key}",
            "provider_url": "https://cms.sandbox.example/drafts/1",
            "created_at": iso_z(self.clock.now()),
            "actual_side_effects": 1,
        }
        assert_valid("PublicationReceipt", rec)
        stored = dict(rec)
        stored["payload_digest"] = digest
        self.ledger.put("cms_effects", key, stored)
        self.ledger.put("cms_by_receipt", rec["publication_id"], rec)
        return rec

    def rollback_own(self, publication_id: str, test_run_id: str) -> dict[str, Any]:
        rec = self.ledger.get("cms_by_receipt", publication_id)
        if not rec:
            raise KeyError(publication_id)
        rec = dict(rec)
        rec["status"] = "CANCELLED"
        rec["actual_side_effects"] = 0
        assert_valid("PublicationReceipt", rec)
        self.ledger.put("cms_by_receipt", publication_id, rec)
        self.ledger.put("cms_rollback", publication_id, {"test_run_id": test_run_id, "status": "ROLLED_BACK"})
        return {"publication_id": publication_id, "status": "ROLLED_BACK", "test_run_id": test_run_id}
