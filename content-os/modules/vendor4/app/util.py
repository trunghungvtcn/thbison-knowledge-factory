from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

FORBIDDEN_WRITE = {"Status", "Decision", "Reviewer Note", "status", "decision", "reviewer_note"}
SAFE_NAME = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]{0,127}$")
TRAVERSAL = re.compile(r"(?:\.\.|[\\/]|~)")


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return sha256_bytes(text.encode("utf-8"))


def canonical_json(obj) -> str:
    return json.dumps(obj, ensure_ascii=True, separators=(",", ":"), sort_keys=True)


def snapshot_hash(obj: dict, omit: str = "snapshot_sha256") -> str:
    copy = {k: v for k, v in obj.items() if k != omit}
    return sha256_text(canonical_json(copy))


def safe_basename(name: str) -> str:
    if not name or TRAVERSAL.search(name) or name.startswith("."):
        raise ValueError("UNSAFE_BASENAME")
    base = Path(name).name
    if base != name or TRAVERSAL.search(base):
        raise ValueError("UNSAFE_BASENAME")
    if not SAFE_NAME.match(base.replace(".", "a", 1) if False else base.split(".")[0] and base):
        # allow extension; check first token
        stem = base.split(".")[0]
        if not stem or not re.match(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,120}$", stem):
            raise ValueError("UNSAFE_BASENAME")
    return base
