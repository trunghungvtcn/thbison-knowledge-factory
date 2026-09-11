"""Build deterministic, sanitized public candidate release assets."""

from __future__ import annotations

import argparse
import hashlib
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXED_TIME = (2026, 9, 10, 0, 0, 0)
AUDIT_FILES = [
    "ACCEPTANCE.md", "AUDIT_REQUEST.json", "CONTRACT_MAPPING.md", "NOTION_READONLY.md",
    "PROMPT_GROK_AUDIT.md", "PUBLICATION.md", "REPORT_CODEX.md", "SOURCE_MANIFEST.json", "SOURCE_SHA",
    "manifests/integration_overlay.json",
]


def add_bytes(zf: zipfile.ZipFile, name: str, data: bytes) -> None:
    info = zipfile.ZipInfo(name, FIXED_TIME)
    info.create_system = 3
    info.external_attr = 0o100644 << 16
    info.compress_type = zipfile.ZIP_DEFLATED
    zf.writestr(info, data)


def zip_files(output: Path, files: list[tuple[str, bytes]]) -> None:
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name, data in sorted(files):
            add_bytes(zf, name.replace("\\", "/"), data)


def git_bytes(revision: str, path: str) -> bytes:
    return subprocess.run(["git", "show", f"{revision}:{path}"], cwd=ROOT, check=True, capture_output=True).stdout


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--revision", required=True)
    parser.add_argument("--output", required=True, type=Path)
    opts = parser.parse_args()
    out = opts.output.resolve()
    out.mkdir(parents=True, exist_ok=True)
    tracked = subprocess.run(
        ["git", "ls-tree", "-r", "--name-only", opts.revision], cwd=ROOT,
        check=True, capture_output=True, text=True,
    ).stdout.splitlines()
    source = []
    for path in tracked:
        if path.startswith("dependencies/"):
            continue
        source.append((f"thbison-integration-01/{path}", git_bytes(opts.revision, path)))
    zip_files(out / "thbison-integration-01-source-sanitized.zip", source)
    zip_files(out / "thbison-integration-01-audit-kit.zip", [(p, git_bytes(opts.revision, p)) for p in AUDIT_FILES])
    evidence_root = ROOT / "content-os" / "evidence-current"
    evidence = []
    if evidence_root.exists():
        for path in evidence_root.rglob("*"):
            if path.is_file() and path.suffix.lower() in {".json", ".txt", ".xml"}:
                evidence.append((path.relative_to(evidence_root).as_posix(), path.read_bytes()))
    evidence.append(("EVIDENCE_SCOPE.json", json.dumps({
        "data_class": "TEST_ONLY", "live_data_pass": False,
        "notion_status": "NOTION_TARGET_MISSING", "public_effects": 0,
    }, indent=2, sort_keys=True).encode() + b"\n"))
    zip_files(out / "thbison-integration-01-evidence-sanitized.zip", evidence)
    assets = sorted(out.glob("*.zip"))
    sums = "".join(f"{hashlib.sha256(p.read_bytes()).hexdigest()}  {p.name}\n" for p in assets)
    (out / "SHA256SUMS").write_text(sums, encoding="ascii", newline="\n")
    print(sums, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
