#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.staging_preflight import run_preflight


def main(argv=None) -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--manifest", default=str(ROOT / "docs" / "STAGING_ACCESS_MANIFEST.json"))
    p.add_argument("--read-only", action="store_true", default=True)
    p.add_argument("--output", default="-")
    args = p.parse_args(argv)
    report = run_preflight(manifest_path=args.manifest, read_only=args.read_only)
    text = json.dumps(report, indent=2)
    if args.output == "-":
        print(text)
    else:
        Path(args.output).write_text(text + "\n", encoding="utf-8")
    if report["status"] in {"BLOCKED_ACCESS", "BLOCKED_OPT_IN"}:
        return 2
    if report["status"] in {"CHANGES_REQUIRED", "TIMEOUT_OR_NETWORK", "BLOCKED_STAGING_RELATIONS"}:
        return 3
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
