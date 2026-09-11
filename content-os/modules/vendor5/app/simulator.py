from __future__ import annotations

import threading
import time
from dataclasses import dataclass
from typing import Literal

from app.errors import AdapterError
from app.hashutil import sha256_utf8

Fault = Literal[
    "none",
    "timeout-after-accept",
    "timeout",
    "unavailable",
    "rate_limited",
    "schema_drift",
    "delayed",
    "4xx",
]


@dataclass
class SimDraft:
    provider_record_id: str
    project_id: str
    destination_id: str
    external_key: str
    article_id: str
    article_revision: int
    content_sha256: str
    revision: int
    body: str
    public: bool = False
    test_run_id: str | None = None
    created_at: str = "2030-01-01T00:00:00Z"
    human_edited: bool = False

    @classmethod
    def from_row(cls, row: dict) -> "SimDraft":
        return cls(
            provider_record_id=row["provider_record_id"],
            project_id=row["project_id"],
            destination_id=row["destination_id"],
            external_key=row["external_key"],
            article_id=row["article_id"],
            article_revision=row["article_revision"],
            content_sha256=row["content_sha256"],
            revision=row["revision"],
            body=row["body"],
            public=bool(row.get("public")),
            test_run_id=row.get("test_run_id"),
            created_at=row["created_at"],
            human_edited=bool(row.get("human_edited")),
        )

    def as_dict(self) -> dict:
        return {
            "provider_record_id": self.provider_record_id,
            "project_id": self.project_id,
            "destination_id": self.destination_id,
            "external_key": self.external_key,
            "article_id": self.article_id,
            "article_revision": self.article_revision,
            "content_sha256": self.content_sha256,
            "revision": self.revision,
            "body": self.body,
            "public": self.public,
            "test_run_id": self.test_run_id,
            "created_at": self.created_at,
            "human_edited": self.human_edited,
        }


class CmsSimulator:
    """Durable CMS provider simulator. Drafts survive adapter process restart."""

    def __init__(self, ledger=None, fault_store: dict | None = None):
        self.ledger = ledger
        self._op_lock = threading.Lock()
        self._mem: dict[str, SimDraft] = {}
        self._by_key: dict[str, str] = {}
        self._mem_calls = 0
        self._mem_effects = 0
        self.fault: Fault = "none"
        self.delay_s = 0.0
        self.lookup_enabled = True
        self.capabilities = {
            "product": "THBISON-CMS-SIM",
            "version": "sim-1.0.0",
            "idempotency": "EXTERNAL_KEY_LOOKUP",
            "revisions": True,
            "public_publish": False,
            "media_lookup": True,
            "durable": True,
        }

    @property
    def create_calls(self) -> int:
        if self.ledger:
            return int(self.ledger.sim_meta_get("create_calls", "0"))
        return self._mem_calls

    @property
    def side_effects(self) -> int:
        if self.ledger:
            return int(self.ledger.sim_meta_get("side_effects", "0"))
        return self._mem_effects

    def reset(self) -> None:
        self.fault = "none"
        self.delay_s = 0.0
        self.lookup_enabled = True
        if self.ledger:
            self.ledger.sim_clear()
        else:
            self._mem.clear()
            self._by_key.clear()
            self._mem_calls = 0
            self._mem_effects = 0

    def set_fault(self, fault: Fault, delay_s: float = 0.0) -> None:
        self.fault = fault
        self.delay_s = delay_s

    def _key(self, project_id: str, destination_id: str, external_key: str) -> str:
        return f"{project_id}|{destination_id}|{external_key}"

    def inspect_capabilities(self) -> dict:
        if self.fault == "schema_drift":
            return {**self.capabilities, "schema_drift": True, "missing_field": "body_html"}
        return dict(self.capabilities)

    def _bump_calls(self) -> None:
        if self.ledger:
            self.ledger.sim_incr("create_calls")
        else:
            self._mem_calls += 1

    def _bump_effects(self) -> None:
        if self.ledger:
            self.ledger.sim_incr("side_effects")
        else:
            self._mem_effects += 1

    def create_draft(self, inp: dict) -> SimDraft:
        if self.delay_s:
            time.sleep(self.delay_s)
        if self.fault == "rate_limited":
            raise AdapterError("RATE_LIMITED", "429 Retry-After: 1", True, 429)
        if self.fault == "unavailable":
            raise AdapterError("PROVIDER_ERROR", "CMS 5xx", True, 503)
        if self.fault == "timeout":
            raise AdapterError("TIMEOUT", "CMS timeout before accept", True, 503)
        if self.fault == "4xx":
            raise AdapterError("VALIDATION_ERROR", "CMS nonretryable 4xx", False, 400)
        if self.fault == "schema_drift":
            raise AdapterError("SCHEMA_DRIFT", "CMS missing required field body_html", False)

        with self._op_lock:
            self._bump_calls()
            existing = self.lookup(inp["project_id"], inp["destination_id"], inp["external_key"])
            if existing:
                return existing
            k = self._key(inp["project_id"], inp["destination_id"], inp["external_key"])
            rid = "cms-" + sha256_utf8(k)[:20]
            draft = SimDraft(
                provider_record_id=rid,
                project_id=inp["project_id"],
                destination_id=inp["destination_id"],
                external_key=inp["external_key"],
                article_id=inp["article_id"],
                article_revision=inp["article_revision"],
                content_sha256=inp["content_sha256"],
                revision=1,
                body=inp["body"],
                public=False,
                test_run_id=inp.get("test_run_id"),
                created_at=inp.get("created_at", "2030-01-01T00:00:00Z"),
            )
            self._store(draft)
            self._bump_effects()
            if self.fault == "timeout-after-accept":
                raise AdapterError("TIMEOUT", "CMS accepted then response lost", True, 503)
            return draft

    def _store(self, draft: SimDraft) -> None:
        if self.ledger:
            self.ledger.sim_put(draft.as_dict())
        else:
            self._mem[draft.provider_record_id] = draft
            self._by_key[self._key(draft.project_id, draft.destination_id, draft.external_key)] = draft.provider_record_id

    def lookup(self, project_id: str, destination_id: str, external_key: str) -> SimDraft | None:
        if not self.lookup_enabled:
            return None
        if self.ledger:
            row = self.ledger.sim_lookup(project_id, destination_id, external_key)
            return SimDraft.from_row(row) if row else None
        rid = self._by_key.get(self._key(project_id, destination_id, external_key))
        return self._mem.get(rid) if rid else None

    def get(self, provider_record_id: str) -> SimDraft | None:
        if self.ledger:
            row = self.ledger.sim_get(provider_record_id)
            return SimDraft.from_row(row) if row else None
        return self._mem.get(provider_record_id)

    def update(self, provider_record_id: str, expected_revision: int, body: str, content_sha256: str) -> SimDraft:
        d = self.get(provider_record_id)
        if not d:
            raise AdapterError("VALIDATION_ERROR", "draft not found")
        if d.revision != expected_revision:
            raise AdapterError("STALE_REVISION", "Optimistic revision mismatch; human changes preserved")
        d.body = body
        d.content_sha256 = content_sha256
        d.revision += 1
        self._store(d)
        return d

    def mark_human_edit(self, provider_record_id: str) -> None:
        d = self.get(provider_record_id)
        if not d:
            raise AdapterError("VALIDATION_ERROR", "draft not found")
        d.human_edited = True
        d.revision += 1
        self._store(d)

    def delete(self, provider_record_id: str) -> None:
        d = self.get(provider_record_id)
        if self.ledger:
            self.ledger.sim_delete(provider_record_id)
        elif d:
            self._mem.pop(provider_record_id, None)
            self._by_key.pop(self._key(d.project_id, d.destination_id, d.external_key), None)
