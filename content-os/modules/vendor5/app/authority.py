from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone

from app.errors import AdapterError


def parse_ts(value: str) -> datetime:
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        raise AdapterError("SCHEDULE_INVALID", "Timezone-less timestamp rejected")
    return dt.astimezone(timezone.utc)


class AuthorityStore:
    """Server-side authoritative records. Client-supplied APPROVED is not trusted."""

    def __init__(self):
        self.approvals: dict[str, dict] = {}
        self.articles: dict[tuple[str, int], dict] = {}
        self.evidence: dict[str, dict] = {}
        self.assets: dict[str, dict] = {}

    def reset(self) -> None:
        self.approvals.clear()
        self.articles.clear()
        self.evidence.clear()
        self.assets.clear()

    def put_approval(self, rec: dict) -> None:
        self.approvals[rec["approval_id"]] = deepcopy(rec)

    def put_article(self, rec: dict) -> None:
        self.articles[(rec["article_id"], rec["article_revision"])] = deepcopy(rec)

    def put_evidence(self, rec: dict) -> None:
        self.evidence[rec["snapshot_sha256"]] = deepcopy(rec)

    def put_asset(self, asset_id: str, sha256: str, url: str, expires_at: str) -> None:
        self.assets[asset_id] = {"sha256": sha256, "url": url, "expires_at": expires_at}

    def get_approval(self, approval_id: str) -> dict:
        rec = self.approvals.get(approval_id)
        if not rec:
            raise AdapterError("MISSING_EVIDENCE", "Authoritative approval not found")
        return deepcopy(rec)

    def revoke(self, approval_id: str) -> None:
        if approval_id in self.approvals:
            self.approvals[approval_id]["decision"] = "REVOKED"

    def get_article(self, article_id: str, revision: int) -> dict:
        rec = self.articles.get((article_id, revision))
        if not rec:
            raise AdapterError("MISSING_EVIDENCE", "Article revision not found")
        return deepcopy(rec)

    def get_evidence(self, snapshot_sha256: str) -> dict:
        rec = self.evidence.get(snapshot_sha256)
        if not rec:
            raise AdapterError("MISSING_EVIDENCE", "Evidence snapshot not found")
        return deepcopy(rec)

    def refresh_asset(self, asset_id: str, expected_sha256: str) -> str:
        a = self.assets.get(asset_id)
        if not a:
            raise AdapterError("ASSET_HASH_MISMATCH", "Unknown asset")
        if a["sha256"] != expected_sha256:
            raise AdapterError("ASSET_HASH_MISMATCH", "Asset bytes hash mismatch")
        return a["url"]
