"""Actual hop clients. Mapping from ContentBrief → V4 query is PROPOSED, not silent remap."""

from __future__ import annotations

from typing import Any

from thbison_v6.adapters.http_client import HttpJsonClient
from thbison_v6.contract_validate import assert_valid


class KnowledgeHttpAdapter:
    kind = "ACTUAL"
    vendor = "VENDOR_4"
    mapping_status = "PROPOSED"
    verified_component = False

    def __init__(self, client: HttpJsonClient):
        self.client = client
        self.transport_name = getattr(client, "transport_name", None)

    def query(self, brief: dict[str, Any]) -> dict[str, Any]:
        # PROPOSED mapping documented; owner must accept. Tested as explicit transform.
        proposed = {
            "project_id": brief["project_id"],
            "product_id": (brief.get("product_refs") or [None])[0],
            "jurisdiction": (brief.get("scope") or {}).get("country_code"),
            "locale": (brief.get("scope") or {}).get("language"),
            "mapping": "PROPOSED_V6_CONTENTBRIEF_TO_V4_QUERY",
        }
        status, body = self.client.call("POST", "/v1/knowledge/query", proposed)
        if status != 200:
            raise RuntimeError(f"KNOWLEDGE_HTTP_{status}")
        assert_valid("EvidenceBundle", body)
        return body


class CmsHttpAdapter:
    kind = "ACTUAL"
    vendor = "VENDOR_5"
    verified_component = False

    def __init__(self, client: HttpJsonClient):
        self.client = client
        self.transport_name = getattr(client, "transport_name", None)

    def publish(self, req: dict[str, Any], approval: dict[str, Any] | None) -> dict[str, Any]:
        status, body = self.client.call(
            "POST",
            "/v1/publish",
            {"request": req, "approval_id": None if not approval else approval.get("approval_id")},
        )
        if status != 200:
            raise RuntimeError(f"CMS_HTTP_{status}")
        assert_valid("PublicationReceipt", body)
        return body
