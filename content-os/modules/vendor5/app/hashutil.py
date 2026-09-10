from __future__ import annotations

import hashlib
import json
from typing import Any


def sha256_hex(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_utf8(text: str) -> str:
    return sha256_hex(text.encode("utf-8"))


def canonical_json(obj: Any) -> str:
    return json.dumps(obj, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def hash_without(obj: dict, omit: str) -> str:
    payload = {k: obj[k] for k in obj if k != omit}
    return sha256_hex(canonical_json(payload).encode("utf-8"))


def payload_hash(obj: dict) -> str:
    return sha256_hex(canonical_json(obj).encode("utf-8"))
