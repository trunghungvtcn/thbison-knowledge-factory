from __future__ import annotations

from pathlib import Path
import json
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(
    r"^(\.venv[^/]*|recovery|data-staging|private-audit|artifacts|outputs|models|checkpoints|farming_input)(/|$)"
    r"|^v166/corpus(/|$)"
)


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
    missing = sorted((tracked - exempt) - manifest_paths)
    extra = sorted(manifest_paths - tracked)
    if missing or extra:
        raise SystemExit(f"manifest mismatch: missing={missing}, extra={extra}")
    oversized = [path for path in tracked if (ROOT / path).stat().st_size > 10 * 1024 * 1024]
    if oversized:
        raise SystemExit(f"files over 10 MiB: {oversized}")
    print(json.dumps({"tracked": len(tracked), "manifested": len(manifest_paths), "status": "PASS"}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
