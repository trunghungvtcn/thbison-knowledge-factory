"""Vendor 4 knowledge/asset gateway simulator (STUB)."""

from __future__ import annotations

from typing import Any

from thbison_v6.contract_validate import assert_valid
from thbison_v6.faults import FaultPlan
from thbison_v6.hashutil import evidence_snapshot_sha256, sha256_hex
from thbison_v6.ledger import FileLedger

QUOTE = (
    "TEST ONLY. Example THB-PILOT has a synthetic housing. "
    "This is synthetic, not a real product claim."
)


class KnowledgeSimulator:
    vendor = "VENDOR_4"
    kind = "STUB"

    def __init__(self, ledger: FileLedger, faults: FaultPlan | None = None):
        self.ledger = ledger
        self.faults = faults or FaultPlan()
        self._seed()

    def _claim(self, status: str = "ELIGIBLE") -> dict[str, Any]:
        qh = sha256_hex(QUOTE)
        return {
            "claim_id": "claim-ref-001",
            "text": QUOTE,
            "status": status,
            "risk": "DESCRIPTIVE",
            "allowed_uses": ["DRAFT", "PUBLISH"] if status == "ELIGIBLE" else [],
            "source_ref": "synthetic-source",
            "source_version": "test-1",
            "source_sha256": qh,
            "locator": "text:1",
            "quote": QUOTE,
            "quote_sha256": qh,
            "applicability": "Synthetic THB-PILOT only",
            "jurisdiction": "VN",
        }

    def _seed(self) -> None:
        if self.ledger.get_map("knowledge"):
            return
        item = {
            "item_id": "ki-001",
            "project_id": "proj-lab",
            "product": "THB-PILOT",
            "jurisdiction": "VN",
            "claim": self._claim("ELIGIBLE"),
        }
        self.ledger.put("knowledge", item["item_id"], item)

    def query(self, brief: dict[str, Any]) -> dict[str, Any]:
        project_id = brief.get("project_id", "proj-lab")
        products = brief.get("product_refs") or []
        jurisdiction = (brief.get("scope") or {}).get("country_code", "VN")
        matches = []
        for item in self.ledger.get_map("knowledge").values():
            if item.get("project_id") != project_id:
                continue
            if products and item.get("product") not in products:
                continue
            if item.get("jurisdiction") != jurisdiction:
                continue
            matches.append(item["claim"])
        bundle = {
            "contract_version": "1.0.0",
            "project_id": project_id,
            "data_class": "TEST_ONLY",
            "bundle_id": "evb-ref-001",
            "snapshot_sha256": "0" * 64,
            "policy_version": "test-policy-1",
            "as_of": "2030-01-01T00:00:00Z",
            "claims": matches,
            "gaps": [] if matches else ["no eligible claims for product/jurisdiction"],
        }
        bundle["snapshot_sha256"] = evidence_snapshot_sha256(bundle)
        assert_valid("EvidenceBundle", bundle)
        self.ledger.put("evidence", bundle["bundle_id"], bundle)
        return bundle

    def set_status(self, item_id: str, status: str) -> None:
        item = self.ledger.get("knowledge", item_id)
        if not item:
            raise KeyError(item_id)
        item = dict(item)
        claim = dict(item["claim"])
        # contract enum has no REVOKED; map to QUARANTINE
        mapped = "QUARANTINE" if status == "REVOKED" else status
        if mapped not in {"ELIGIBLE", "HOLD", "QUARANTINE"}:
            mapped = "QUARANTINE"
        claim["status"] = mapped
        claim["allowed_uses"] = ["DRAFT", "PUBLISH"] if mapped == "ELIGIBLE" else []
        item["claim"] = claim
        self.ledger.put("knowledge", item_id, item)

    def current_policy(self, item_ids: list[str]) -> dict[str, str]:
        out = {}
        for i in item_ids:
            item = self.ledger.get("knowledge", i) or {}
            out[i] = (item.get("claim") or {}).get("status", "MISSING")
        return out

    def asset_put(self, project_id: str, name: str, data: bytes) -> dict[str, Any]:
        if ".." in name or name.startswith("/"):
            raise ValueError("TRAVERSAL_REJECTED")
        digest = sha256_hex(data)
        rec = {
            "asset_id": digest[:16],
            "project_id": project_id,
            "name": name,
            "size": len(data),
            "sha256": digest,
            "url": f"https://signed.example/{digest[:16]}?exp=1",
        }
        existing = self.ledger.get("assets", rec["asset_id"])
        if existing and existing.get("sha256") != digest:
            raise ValueError("COLLISION_REJECTED")
        self.ledger.put("assets", rec["asset_id"], rec)
        return rec

    def refresh_url(self, asset_id: str) -> dict[str, Any]:
        rec = dict(self.ledger.get("assets", asset_id))
        rec["url"] = rec["url"].split("?")[0] + "?exp=2"
        self.ledger.put("assets", asset_id, rec)
        return rec
