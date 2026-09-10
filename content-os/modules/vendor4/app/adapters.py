"""Internal adapter boundary. Map Notion/file services after handoff without changing policy core."""

from __future__ import annotations

from typing import Protocol


class KnowledgeAdapter(Protocol):
    def list_claims(self, project_id: str) -> list[dict]: ...


class AssetAdapter(Protocol):
    def attach(self, asset_id: str, blob: bytes) -> dict: ...


class SyntheticAdapter:
    """In-process simulator. Do not embed production IDs."""

    def list_claims(self, project_id: str) -> list[dict]:
        from .store import STORE

        return [r for r in STORE.knowledge if r["project_id"] == project_id]

    def attach(self, asset_id: str, blob: bytes) -> dict:
        return {"asset_id": asset_id, "bytes": len(blob), "mode": "SYNTHETIC"}


MAPPING_NOTES = """
Pin STAGING_SOURCE_REVISION and STAGING_SCHEMA_REVISION from environment.
Do not hardcode Notion page IDs or data-source IDs in runtime policy.
Use STAGING_ACCESS_MANIFEST.json as operator input only.
"""
