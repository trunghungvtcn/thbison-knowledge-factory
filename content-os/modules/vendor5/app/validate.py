from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from jsonschema.exceptions import ValidationError

from app.errors import AdapterError

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "contracts" / "schemas"
FORMAT = FormatChecker()


def _load(name: str) -> dict:
    return json.loads((SCHEMA_DIR / name).read_text(encoding="utf-8"))


VALIDATORS = {
    n: Draft202012Validator(_load(n + ".json"), format_checker=FORMAT)
    for n in (
        "PublishRequest",
        "PublicationReceipt",
        "ArticlePackage",
        "ApprovalRecord",
        "EvidenceBundle",
        "CapabilitiesReply",
        "Error",
    )
}


def validate(name: str, obj: Any) -> dict:
    if not isinstance(obj, dict):
        raise AdapterError("VALIDATION_ERROR", f"{name} must be object")
    v = VALIDATORS[name]
    errors = sorted(v.iter_errors(obj), key=lambda e: list(e.absolute_path))
    if errors:
        first = errors[0]
        path = ".".join(str(p) for p in first.absolute_path) or name
        raise AdapterError("VALIDATION_ERROR", f"{name} invalid at {path}: {first.message}")
    return obj
