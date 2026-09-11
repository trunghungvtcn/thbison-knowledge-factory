from __future__ import annotations

from pathlib import Path

PIN_FILE = "CONTRACT_SHA256.txt"


def expected_digest(root: Path | None = None) -> str:
    root = root or Path(__file__).resolve().parents[2]
    return (root / PIN_FILE).read_text(encoding="utf-8").strip()


def reject_unknown_fields(obj: dict, allowed: set[str]) -> None:
    extra = set(obj) - allowed
    if extra:
        raise ValueError(f"UNKNOWN_FIELDS:{sorted(extra)}")


def reject_tz_naive_display_policy(tz_name: str) -> None:
    if tz_name != "Asia/Bangkok":
        raise ValueError("TIMEZONE_VIOLATION")
