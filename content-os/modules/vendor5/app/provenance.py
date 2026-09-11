from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def code_commit() -> str:
    env = os.environ.get("SOURCE_REVISION", "").strip()
    if env:
        return env
    p = ROOT / "SOURCE_REVISION"
    if p.is_file():
        text = p.read_text(encoding="utf-8").strip()
        if text:
            return text.split()[0][:64]
    return "UNKNOWN"


def native_status(app_mode: str, cms_base: str, cms_token: str, probe_verified: bool) -> str:
    if app_mode == "MOCK":
        return "MOCK"
    if not (cms_base and cms_token):
        return "BLOCKED_MISSING_INPUT"
    if probe_verified:
        return "VERIFIED"
    return "CONFIGURED_UNVERIFIED"
