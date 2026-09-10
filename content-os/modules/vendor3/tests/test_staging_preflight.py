"""CLI preflight without token is BLOCKED_ACCESS."""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_preflight_blocked_without_token():
    env = {k: v for k, v in os.environ.items() if k not in {"STAGING_NOTION_TOKEN", "NOTION_STAGING_TOKEN", "STAGING_TOKEN"}}
    p = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "staging_preflight.py"),
         "--manifest", str(ROOT / "STAGING_ACCESS_MANIFEST.json"),
         "--read-only", "--output", str(ROOT / "evidence" / "staging_preflight.json")],
        capture_output=True, text=True, env=env, check=False,
    )
    assert p.returncode == 2
    data = json.loads(p.stdout)
    assert data["status"] == "BLOCKED_ACCESS"


def test_manifest_present_in_source():
    m = json.loads((ROOT / "STAGING_ACCESS_MANIFEST.json").read_text())
    assert m["credential_delivery"].startswith("OUT_OF_BAND")
