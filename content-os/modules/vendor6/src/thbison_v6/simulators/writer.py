"""Vendor 2 writer/approval simulator (STUB)."""

from __future__ import annotations

from typing import Any

from thbison_v6.contract_validate import assert_valid
from thbison_v6.faults import FaultPlan
from thbison_v6.hashutil import article_content_sha256
from thbison_v6.ledger import Clock, FileLedger
from thbison_v6.timefmt import iso_z


class WriterSimulator:
    vendor = "VENDOR_2"
    kind = "STUB"

    def __init__(self, ledger: FileLedger, clock: Clock, faults: FaultPlan | None = None):
        self.ledger = ledger
        self.clock = clock
        self.faults = faults or FaultPlan()

    def draft(self, brief: dict[str, Any], bundle: dict[str, Any]) -> dict[str, Any]:
        claims = list(bundle.get("claims") or [])
        if not claims:
            raise PermissionError("EVIDENCE_BLOCKED")
        for c in claims:
            if c.get("status") in {"HOLD", "QUARANTINE"}:
                raise PermissionError("EVIDENCE_BLOCKED")
            if "DRAFT" not in (c.get("allowed_uses") or []):
                raise PermissionError("EVIDENCE_BLOCKED")
        first = claims[0]
        article = {
            "contract_version": "1.0.0",
            "project_id": brief["project_id"],
            "data_class": "TEST_ONLY",
            "article_id": "art-ref-001",
            "article_revision": 1,
            "brief_id": brief["brief_id"],
            "brief_revision": brief["brief_revision"],
            "bundle_id": bundle["bundle_id"],
            "evidence_snapshot_sha256": bundle["snapshot_sha256"],
            "policy_version": bundle["policy_version"],
            "title": brief["title"],
            "slug": "pilot-article",
            "status": "PREVIEW_READY",
            "blocks": [
                {
                    "block_id": "p1",
                    "kind": "FACTUAL",
                    "text": first["quote"],
                    "claim_ids": [first["claim_id"]],
                }
            ],
            "seo": {"title": "TEST title", "description": "TEST description"},
            "unresolved_claim_ids": [],
            "publication_blockers": [],
            "content_sha256": "0" * 64,
        }
        article["content_sha256"] = article_content_sha256(article)
        assert_valid("ArticlePackage", article)
        self.ledger.put("articles", article["article_id"], article)
        self.ledger.put("article_claims", article["article_id"], claims)
        return article

    def mutate(self, article_id: str, title: str) -> dict[str, Any]:
        art = dict(self.ledger.get("articles", article_id))
        art["title"] = title
        art["article_revision"] = int(art.get("article_revision", 1)) + 1
        art["content_sha256"] = "0" * 64
        art["content_sha256"] = article_content_sha256(art)
        assert_valid("ArticlePackage", art)
        self.ledger.put("articles", article_id, art)
        return art

    def approve(
        self,
        article: dict[str, Any],
        destination_id: str,
        ttl_s: float = 3600,
        human_role: str = "editor",
    ) -> dict[str, Any]:
        if human_role not in {"editor", "publisher"}:
            raise PermissionError("HUMAN_ROLE_REQUIRED")
        now = self.clock.now()
        rec = {
            "contract_version": "1.0.0",
            "project_id": article["project_id"],
            "data_class": "TEST_ONLY",
            "approval_id": f"appr-{article['article_id']}-{article['article_revision']}",
            "article_id": article["article_id"],
            "article_revision": article["article_revision"],
            "content_sha256": article["content_sha256"],
            "evidence_snapshot_sha256": article["evidence_snapshot_sha256"],
            "policy_version": article["policy_version"],
            "destination_id": destination_id,
            "decision": "APPROVED",
            "approved_by": "test-human-editor",
            "approved_at": iso_z(now),
            "expires_at": iso_z(now + ttl_s),
        }
        assert_valid("ApprovalRecord", rec)
        self.ledger.put("approvals", rec["approval_id"], rec)
        self.ledger.put("approval_expires_epoch", rec["approval_id"], now + ttl_s)
        return rec

    def revoke(self, approval_id: str) -> None:
        rec = dict(self.ledger.get("approvals", approval_id))
        rec["decision"] = "REVOKED"
        assert_valid("ApprovalRecord", rec)
        self.ledger.put("approvals", approval_id, rec)

    def get_approval(self, approval_id: str) -> dict[str, Any] | None:
        rec = self.ledger.get("approvals", approval_id)
        if not rec:
            return None
        rec = dict(rec)
        exp = self.ledger.get("approval_expires_epoch", approval_id)
        if rec.get("decision") == "APPROVED" and exp is not None and float(exp) <= self.clock.now():
            rec["decision"] = "REVOKED"
            self.ledger.put("approvals", approval_id, rec)
        return rec

    def is_expired(self, approval_id: str) -> bool:
        exp = self.ledger.get("approval_expires_epoch", approval_id)
        if exp is None:
            return False
        return float(exp) <= self.clock.now()
