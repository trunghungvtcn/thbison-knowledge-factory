"""Pin formatting and transport allow-list. No contractor internals."""
from __future__ import annotations

from typing import Any
import re

from .mapping import J1_REVIEWED, J2_PUBLISHED

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "CANCELLED", "RECONCILE_REQUIRED"})


def transport_is_allowed(transport: Any) -> bool:
    return getattr(transport, "LOCAL_SHADOW_ALLOWED", None) is True


def mark_allowed(transport: Any) -> Any:
    setattr(transport, "LOCAL_SHADOW_ALLOWED", True)
    return transport


def normalize_pins(
    *,
    j1_commit_sha: str | None,
    j1_input_hash: str | None,
    j2_commit_sha: str | None,
    j2_input_hash: str | None,
    j1_input_sha: str | None,
    j2_env_sha: str | None,
) -> dict[str, str | None]:
    j1c = (j1_commit_sha or "").lower() or None
    j1h = (j1_input_hash or "").lower() or None
    j2c = (j2_commit_sha or "").lower() or None
    j2h = (j2_input_hash or "").lower() or None
    legacy1 = (j1_input_sha or "").lower() or None
    legacy2 = (j2_env_sha or "").lower() or None
    if legacy1 and _COMMIT_RE.match(legacy1):
        j1c = j1c or legacy1
    elif legacy1 and _HASH_RE.match(legacy1):
        j1h = j1h or legacy1
    if legacy2 and _COMMIT_RE.match(legacy2):
        j2c = j2c or legacy2
    elif legacy2 and _HASH_RE.match(legacy2):
        j2h = j2h or legacy2
    return {
        "j1_commit_sha": j1c,
        "j1_input_hash": j1h,
        "j2_commit_sha": j2c,
        "j2_input_hash": j2h,
    }


def pin_record(raw: dict[str, str | None]) -> dict[str, Any]:
    return {
        "j1_commit_sha": raw["j1_commit_sha"],
        "j1_input_hash": raw["j1_input_hash"],
        "j1_commit_format_ok": bool(raw["j1_commit_sha"] and _COMMIT_RE.match(raw["j1_commit_sha"] or "")),
        "j1_input_format_ok": bool(raw["j1_input_hash"] and _HASH_RE.match(raw["j1_input_hash"] or "")),
        "j1_commit_published": raw["j1_commit_sha"] == J1_REVIEWED,
        "j1_input_verified": False,
        "j2_commit_sha": raw["j2_commit_sha"],
        "j2_input_hash": raw["j2_input_hash"],
        "j2_commit_format_ok": bool(raw["j2_commit_sha"] and _COMMIT_RE.match(raw["j2_commit_sha"] or "")),
        "j2_input_format_ok": bool(raw["j2_input_hash"] and _HASH_RE.match(raw["j2_input_hash"] or "")),
        "j2_commit_published": raw["j2_commit_sha"] == J2_PUBLISHED,
        "j2_input_verified": False,
    }


def holds_for_pins(pins: dict[str, Any]) -> list[str]:
    holds: list[str] = []
    if not pins["j1_commit_sha"]:
        holds.append("BLOCKED_INPUT:J1_COMMIT_SHA_MISSING")
    elif not pins["j1_commit_format_ok"]:
        holds.append("BLOCKED_INPUT:J1_COMMIT_SHA_MALFORMED")
    if not pins["j1_input_hash"]:
        holds.append("BLOCKED_INPUT:J1_INPUT_HASH_MISSING")
    elif not pins["j1_input_format_ok"]:
        holds.append("BLOCKED_INPUT:J1_INPUT_HASH_MALFORMED")
    if not pins["j2_commit_sha"]:
        holds.append("BLOCKED_INPUT:J2_COMMIT_SHA_MISSING")
    elif not pins["j2_commit_format_ok"]:
        holds.append("BLOCKED_INPUT:J2_COMMIT_SHA_MALFORMED")
    if not pins["j2_input_hash"]:
        holds.append("BLOCKED_INPUT:J2_INPUT_HASH_MISSING")
    elif not pins["j2_input_format_ok"]:
        holds.append("BLOCKED_INPUT:J2_INPUT_HASH_MALFORMED")
    return holds
