"""Pin formatting and transport allow-list. No contractor internals."""
from __future__ import annotations

from typing import Any
import re

from .mapping import J1_REVIEWED, J2_PUBLISHED

_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_HASH_RE = re.compile(r"^[0-9a-f]{64}$")
TERMINAL_STATES = frozenset({"SUCCEEDED", "FAILED", "CANCELLED", "RECONCILE_REQUIRED"})

# INTERNAL-BRIDGE-01 environment / publication pins. Vendor mapping.J2_PUBLISHED
# stays at the historical 5e61619 record and is not rewritten here.
J2_ENV_COMMIT = "8b197d67f70f6db614a8aefdda7b84f0d4009827"
J1_INVENTORY_COMMIT = "b9e291fb84ddf99a6e6dd662ae122f39326f4d41"
J1_PUBLISHED_INVENTORY_DIGEST = "318a7db871bb056e321d75d18063b9267ece121d7a36f604aaca08ca167f7c89"
J1_LIVE_INVENTORY_CONTENT_HASH = "86165e109bc105975e831e077e60377353811947ff2e7aa7da2a64bb5d88d277"
J2_JUNIT_SHA256 = "fccd4eeab5f897e882937d7cd36081e09786a773df237981f4c57d3240223962"

# Never treat these as HASH_VERIFIED of a private corpus.
_UNVERIFIED_PUBLISHED = {
    J1_PUBLISHED_INVENTORY_DIGEST: "PUBLISHED_UNVERIFIED",
    J1_LIVE_INVENTORY_CONTENT_HASH: "PUBLISHED_UNVERIFIED",
    J2_JUNIT_SHA256: "ENVIRONMENT_UNVERIFIED",
}


def transport_is_allowed(transport: Any) -> bool:
    """Exact FakeTransport only. Self-declared flags and subclasses are denied."""
    try:
        from grok_notion_projection import FakeTransport
    except ImportError:
        return False
    return type(transport) is FakeTransport


def mark_allowed(transport: Any) -> Any:
    """Vendor compatibility shim. LOCAL_SHADOW_ALLOWED is not an allow-list."""
    try:
        setattr(transport, "LOCAL_SHADOW_ALLOWED", True)
    except Exception:
        pass
    return transport


def classify_hash(value: str | None, *, role: str) -> str:
    if not value:
        return "MISSING"
    if not _HASH_RE.match(value):
        return "MALFORMED"
    if len(set(value)) == 1:
        return "SYNTHETIC"
    published = _UNVERIFIED_PUBLISHED.get(value)
    if published:
        return published
    if role == "environment":
        return "ENVIRONMENT_UNVERIFIED"
    return "UNVERIFIED"


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
    j1_hash_status = classify_hash(raw["j1_input_hash"], role="input")
    j2_hash_status = classify_hash(raw["j2_input_hash"], role="environment")
    return {
        "j1_commit_sha": raw["j1_commit_sha"],
        "j1_input_hash": raw["j1_input_hash"],
        "j1_commit_format_ok": bool(raw["j1_commit_sha"] and _COMMIT_RE.match(raw["j1_commit_sha"] or "")),
        "j1_input_format_ok": bool(raw["j1_input_hash"] and _HASH_RE.match(raw["j1_input_hash"] or "")),
        "j1_commit_published": raw["j1_commit_sha"] == J1_REVIEWED,
        "j1_input_verified": False,
        "j1_hash_status": j1_hash_status,
        "j2_commit_sha": raw["j2_commit_sha"],
        "j2_input_hash": raw["j2_input_hash"],
        "j2_commit_format_ok": bool(raw["j2_commit_sha"] and _COMMIT_RE.match(raw["j2_commit_sha"] or "")),
        "j2_input_format_ok": bool(raw["j2_input_hash"] and _HASH_RE.match(raw["j2_input_hash"] or "")),
        "j2_commit_published": raw["j2_commit_sha"] == J2_PUBLISHED,
        "j2_env_commit_known": raw["j2_commit_sha"] == J2_ENV_COMMIT,
        "j2_input_verified": False,
        "j2_hash_status": j2_hash_status,
        "j2_role": "environment",
        "pin_roles": {
            "code_commit": "j1_commit_sha",
            "environment": "j2_commit_sha",
            "input_hash": "j1_input_hash",
            "environment_hash": "j2_input_hash",
        },
        "real_data": False,
        "hash_verified": False,
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
