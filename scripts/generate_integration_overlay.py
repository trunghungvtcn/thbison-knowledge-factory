"""Generate the exact staged-file overlay for THBISON-INTEGRATION-01."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CORE = "3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b"
OUTPUT = "manifests/integration_overlay.json"
J2_OVERLAY = re.compile(r"^(scripts/jobs/j2_|docs/jobs/J2)")


def git(*args: str, binary: bool = False):
    return subprocess.run(
        ["git", *args], cwd=ROOT, check=True, capture_output=True,
        text=not binary,
    ).stdout


def main() -> int:
    migration = json.loads((ROOT / "manifests/migration_assets.json").read_text(encoding="utf-8"))
    historical = {
        item["relative_path"] for item in migration["assets"]
        if item.get("destination") == "GITHUB"
    }
    stage = {}
    for line in git("ls-files", "--stage").splitlines():
        mode, oid, _stage, path = line.split(None, 3)
        stage[path] = (mode, oid)
    changed = set(git("diff", "--name-only", CORE, "--").splitlines())
    exemptions = {"manifests/migration_assets.json", OUTPUT}
    paths = sorted(
        (changed - exemptions - {p for p in changed if J2_OVERLAY.search(p)})
        | ((set(stage) - historical - exemptions) - {p for p in stage if J2_OVERLAY.search(p)})
    )
    entries = []
    for path in paths:
        mode, oid = stage[path]
        if mode == "160000":
            entries.append({"path": path, "kind": "gitlink", "git_sha": oid})
        else:
            blob = git("show", f":{path}", binary=True)
            entries.append({
                "path": path,
                "kind": "file",
                "sha256": hashlib.sha256(blob).hexdigest(),
                "bytes": len(blob),
            })
    payload = {
        "schema_version": "1.0.0",
        "base_core_sha": CORE,
        "note": "Exact staged integration overlay; this manifest intentionally excludes itself and the historical J2 overlay.",
        "entries": entries,
    }
    (ROOT / OUTPUT).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(f"WROTE {OUTPUT}: {len(entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
