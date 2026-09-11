"""Canonical hashing matching contracts/BEHAVIOR.md."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def sha256_hex(data: bytes | str) -> str:
    if isinstance(data, str):
        data = data.encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def object_hash(obj: dict, omit_field: str) -> str:
    copy = {k: v for k, v in obj.items() if k != omit_field}
    return sha256_hex(canonical_json(copy))


def payload_digest(obj: Any) -> str:
    return sha256_hex(canonical_json(obj))


def evidence_snapshot_sha256(bundle: dict) -> str:
    return object_hash(bundle, "snapshot_sha256")


def article_content_sha256(article: dict) -> str:
    return object_hash(article, "content_sha256")
