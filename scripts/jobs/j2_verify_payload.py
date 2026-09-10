"""J2 wrapper around scripts/verify_migration_payload.py.

The recovered-tree verifier requires every tracked GitHub path to appear in
manifests/migration_assets.json. J2 must add scripts/jobs/j2_* and docs/jobs/J2*
(job overlay, not recovered assets) and must not rewrite that manifest (J1).

This wrapper applies the same forbidden-path, size, and membership checks,
then exempts only J2 overlay paths. Any other mismatch still fails.
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

FORBIDDEN = re.compile(
    r"^(\.venv[^/]*|recovery|data-staging|private-audit|artifacts|outputs|models|checkpoints|farming_input)(/|$)"
    r"|^v166/corpus(/|$)"
)
J2_OVERLAY = re.compile(r"^(scripts/jobs/j2_|docs/jobs/J2)")


def main() -> int:
    manifest = json.loads((ROOT / "manifests" / "migration_assets.json").read_text(encoding="utf-8"))
    tracked = set(subprocess.run(
        ["git", "ls-files"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines())
    forbidden = sorted(path for path in tracked if FORBIDDEN.search(path))
    if forbidden:
        raise SystemExit(f"forbidden tracked paths: {forbidden}")
    manifest_paths = {
        asset["relative_path"]
        for asset in manifest["assets"]
        if asset.get("destination") == "GITHUB"
    }
    exempt = {"manifests/migration_assets.json"}
    overlay = {path for path in tracked if J2_OVERLAY.search(path)}
    missing = sorted((tracked - exempt - overlay) - manifest_paths)
    extra = sorted(manifest_paths - tracked)
    if missing or extra:
        raise SystemExit(f"manifest mismatch: missing={missing}, extra={extra}")
    unexpected_overlay = sorted(path for path in overlay if not J2_OVERLAY.search(path))
    if unexpected_overlay:
        raise SystemExit(f"overlay exemption leak: {unexpected_overlay}")
    oversized = [path for path in tracked if (ROOT / path).stat().st_size > 10 * 1024 * 1024]
    if oversized:
        raise SystemExit(f"files over 10 MiB: {oversized}")
    print(json.dumps(
        {
            "tracked": len(tracked),
            "manifested": len(manifest_paths),
            "j2_overlay": sorted(overlay),
            "status": "PASS",
        },
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
