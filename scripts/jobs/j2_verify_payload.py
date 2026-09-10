"""J2 wrapper around scripts/verify_migration_payload.py.

The recovered-tree verifier requires every tracked GitHub path to appear in
manifests/migration_assets.json. J2 must add scripts/jobs/j2_* and docs/jobs/J2*
(job overlay, not recovered assets) and must not rewrite that manifest (J1).

This wrapper applies the same forbidden-path, size, and membership checks,
then exempts only J2 overlay paths. Any other mismatch still fails.
"""
from __future__ import annotations

import json
import hashlib
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
INTEGRATION_MANIFEST = "manifests/integration_overlay.json"


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
    integration = json.loads((ROOT / INTEGRATION_MANIFEST).read_text(encoding="utf-8"))
    exempt.add(INTEGRATION_MANIFEST)
    integration_paths = {entry["path"] for entry in integration["entries"]}
    changed = set(subprocess.run(
        ["git", "diff", "--name-only", integration["base_core_sha"], "--"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines())
    expected_integration = (changed - exempt - overlay) | ((tracked - exempt - overlay) - manifest_paths)
    if integration_paths != expected_integration:
        raise SystemExit(
            "integration overlay mismatch: "
            f"missing={sorted(expected_integration - integration_paths)}, "
            f"extra={sorted(integration_paths - expected_integration)}"
        )
    stage_lines = subprocess.run(
        ["git", "ls-files", "--stage"], cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    stage = {line.split(None, 3)[3]: (line.split(None, 3)[0], line.split(None, 3)[1]) for line in stage_lines}
    for entry in integration["entries"]:
        path = entry["path"]
        mode, git_oid = stage[path]
        if mode == "160000":
            if entry != {"path": path, "kind": "gitlink", "git_sha": git_oid}:
                raise SystemExit(f"integration gitlink mismatch: {path}")
        else:
            blob = subprocess.run(
                ["git", "show", f":{path}"], cwd=ROOT, check=True, capture_output=True,
            ).stdout
            digest = hashlib.sha256(blob).hexdigest()
            if entry != {"path": path, "kind": "file", "sha256": digest, "bytes": len(blob)}:
                raise SystemExit(f"integration file mismatch: {path}")
    missing = sorted((tracked - exempt - overlay - integration_paths) - manifest_paths)
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
            "integration_overlay": len(integration_paths),
            "status": "PASS",
        },
        sort_keys=True,
    ))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
