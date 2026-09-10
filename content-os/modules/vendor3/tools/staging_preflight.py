#!/usr/bin/env python3
"""CLI wrapper. Token only from env, never argv.

  python tools/staging_preflight.py --manifest STAGING_ACCESS_MANIFEST.json --read-only --output evidence/staging_preflight.json

Env:
  STAGING_NOTION_TOKEN   primary
  NOTION_STAGING_TOKEN   alias
  STAGING_TOKEN          alias
  STAGING_ENABLED=true   required for live HTTP
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.staging_preflight import run_preflight  # noqa: E402


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default=str(ROOT / "STAGING_ACCESS_MANIFEST.json"))
    p.add_argument("--read-only", action="store_true", default=True)
    p.add_argument("--output", default="")
    args = p.parse_args()
    manifest = json.loads(Path(args.manifest).read_text())
    code, report = run_preflight(manifest, output_path=args.output or None, read_only=True)
    print(json.dumps({k: v for k, v in report.items() if k != "token"}, indent=2))
    return code


if __name__ == "__main__":
    sys.exit(main())
