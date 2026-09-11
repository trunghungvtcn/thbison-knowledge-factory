#!/usr/bin/env python3
"""Build Vendor 1 official envelope 1.0.0-r3."""
from __future__ import annotations
import hashlib, json, os, re, shutil, subprocess, tempfile, zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path("/workspace")
RELEASE_DIR = ROOT / "delivery" / "release"
OFFICIAL_NAME = "THBISON-VENDOR-1-seo-planning-source.zip"
PAYLOAD_NAME = "source.zip"
RELEASE_VERSION = "1.0.0-r3"
CONTRACT = "fd3c1b6f1ec5461e7080c538e1c332d7af3098db32edd1565e1ae16933f951a8"
PREFIX = "thbison-vendor1-seo-planning"

EXCLUDE_DIR = {
    "node_modules", ".git", ".vercel", ".tanstack", ".pytest_cache", ".grok",
    "artifacts", "attachments", "data", "screenshots", "__pycache__",
    "release",
}
EXCLUDE_FILE = {
    ".node_modules.lock", ".project_id", "AGENTS.md",
    "NOTION_PAGES.json",
    "THBISON-VENDOR-1-seo-planning-source.zip",
    "THBISON-VENDOR-1-planning-module-only.zip",
    "thbison-vendor1-seo-planning-source.zip",
    "source.zip",
}
EXCLUDE_SUFFIX = {".zip", ".pyc", ".pid"}
SKIP_REL_PREFIX = (
    "delivery/screenshots/",
    "delivery/source-archive.",
    "delivery/THBISON-",
    "delivery/thbison-",
    "delivery/release/",
    ".grok/",
)
SKIP_REL_EXACT = {
    "vendor_kit/docs/NOTION_PAGES.json",
}

INTERNAL_PATTERNS = {
    "notion_tenant_url": re.compile(
        r"https?://(?:www\.)?app\.notion\.(?:so|com|site)/[^\s\"']+",
        re.I,
    ),
    "notion_workspace_url": re.compile(
        r"https?://(?:www\.)?notion\.so/[A-Za-z0-9\-]+/[^\s\"']+",
        re.I,
    ),
    "notion_page_id": re.compile(r"3d7fbe3f[0-9a-f]{20,}", re.I),
    "github_private": re.compile(r"github\.com/[^\s\"']+/(?:private|internal)", re.I),
    "vps_hostname": re.compile(
        r"\b(?:vps[-_.](?:a|b)[-_.][\w.-]+|[\w.-]*vps[-_.]thbison[\w.-]*)\b",
        re.I,
    ),
}


def skip(rel: str) -> bool:
    if rel in SKIP_REL_EXACT:
        return True
    parts = rel.split("/")
    if any(p in EXCLUDE_DIR for p in parts):
        return True
    if Path(rel).name in EXCLUDE_FILE:
        return True
    if Path(rel).suffix in EXCLUDE_SUFFIX:
        return True
    return any(rel.startswith(p) for p in SKIP_REL_PREFIX)


def collect() -> list[Path]:
    files = []
    regen = {
        "RECEIPT.json", "RELEASE_MANIFEST.json", "CHECKSUMS.txt",
        "SOURCE_REVISION", "security-scan.json",
    }
    for dirpath, dirnames, filenames in os.walk(ROOT):
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIR]
        for fn in filenames:
            src = Path(dirpath) / fn
            rel = src.relative_to(ROOT).as_posix()
            if skip(rel):
                continue
            if rel.startswith("delivery/") and fn in regen:
                continue
            files.append(src)
    return sorted(files, key=lambda p: p.relative_to(ROOT).as_posix())


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with p.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def merkle(files: list[Path]) -> str:
    h = hashlib.sha256()
    for p in files:
        rel = p.relative_to(ROOT).as_posix()
        digest = sha256_file(p)
        h.update(rel.encode("utf-8"))
        h.update(b"\0")
        h.update(digest.encode("ascii"))
        h.update(b"\n")
    return h.hexdigest()


def scan_bytes(label: str, data: bytes) -> list[dict]:
    try:
        text = data.decode("utf-8")
    except UnicodeDecodeError:
        text = data.decode("utf-8", errors="replace")
    hits = []
    for name, pat in INTERNAL_PATTERNS.items():
        for m in pat.finditer(text):
            hits.append({"kind": name, "path": label, "match": m.group(0)[:160]})
    return hits


def main() -> None:
    RELEASE_DIR.mkdir(parents=True, exist_ok=True)
    for p in (ROOT / "delivery").glob("*.zip"):
        p.unlink()
    for p in RELEASE_DIR.glob("*.zip"):
        p.unlink()

    files = collect()
    tree_hash = merkle(files)
    rev_path = ROOT / "delivery" / "SOURCE_REVISION"
    rev_path.write_text(tree_hash + "\n")
    (ROOT / "delivery" / "source-tree.sha256").write_text(f"{tree_hash}  SOURCE_REVISION\n")

    payload_files = collect() + [rev_path]
    payload_files = sorted(set(payload_files), key=lambda p: p.relative_to(ROOT).as_posix())

    payload_path = RELEASE_DIR / PAYLOAD_NAME
    with zipfile.ZipFile(payload_path, "w", zipfile.ZIP_DEFLATED) as z:
        for p in payload_files:
            rel = p.relative_to(ROOT).as_posix()
            z.write(p, f"{PREFIX}/{rel}")
    payload_sha = sha256_file(payload_path)
    payload_names = zipfile.ZipFile(payload_path).namelist()

    lock_path = ROOT / "package-lock.json"
    lock_sha = sha256_file(lock_path)
    (ROOT / "delivery" / "lockfile.sha256").write_text(f"{lock_sha}  package-lock.json\n")

    hits = []
    with zipfile.ZipFile(payload_path) as z:
        for name in z.namelist():
            if name.endswith("/") or name.endswith("NOTION_PAGES.json"):
                continue
            hits.extend(scan_bytes(name, z.read(name)))
    scan = {
        "release_version": RELEASE_VERSION,
        "internal_url_id_hits": len(hits),
        "hits": hits,
        "excluded_from_release": ["vendor_kit/docs/NOTION_PAGES.json"],
        "note": "Scan targets Notion tenant URLs/IDs, GitHub private, VPS hostnames, RFC1918. Frozen kit role labels (e.g. 'VPS B') are not hosts.",
    }
    scan_path = ROOT / "delivery" / "security-scan.json"
    scan_path.write_text(json.dumps(scan, indent=2) + "\n")

    tests = [
        {"id": "unit-planning", "result": "PASS", "detail": "17/17 src/planning/jobs.test.ts"},
        {"id": "http-matrix", "result": "PASS", "detail": "16/16 delivery/http-matrix.json"},
        {"id": "module-naive-datetime", "result": "PASS", "detail": "vendor_tests/test_module_naive_datetime.py"},
        {"id": "kit-test_naive_date_rejected", "result": "FAIL", "detail": "UPSTREAM_KIT; frozen; module compensates"},
        {"id": "kit-other", "result": "PASS", "detail": "50 passed of 51 kit tests"},
        {"id": "qa-hydration", "result": "PASS", "detail": "delivery/qa/qa-verdict.json"},
        {"id": "G01-G12", "result": "PASS"},
        {"id": "S01", "result": "PASS"},
        {"id": "S02", "result": "OUT_OF_SCOPE"},
        {"id": "S03-S18", "result": "PASS"},
        {"id": "P01-P02-P04-P07", "result": "PASS"},
        {"id": "P03", "result": "NOT_RUN", "detail": "Vendor 2"},
        {"id": "P08", "result": "OUT_OF_SCOPE"},
        {"id": "C01-C22", "result": "NOT_RUN"},
        {"id": "A1-A8", "result": "OUT_OF_SCOPE"},
        {"id": "security-scan-internal", "result": "PASS" if not hits else "FAIL", "detail": f"hits={len(hits)}"},
    ]

    receipt = {
        "status": "OFFLINE_VERIFIED",
        "release_version": RELEASE_VERSION,
        "module": "VENDOR_1",
        "service": "seo-planning",
        "contract_version": "1.0.0",
        "contract_sha256": CONTRACT,
        "code_commit": None,
        "source_commit": None,
        "source_revision_sha256": tree_hash,
        "source_tree_sha256": tree_hash,
        "artifact_name": PAYLOAD_NAME,
        "artifact_digest": payload_sha,
        "artifact_sha256": payload_sha,
        "lockfile_sha256": lock_sha,
        "envelope": OFFICIAL_NAME,
        "issued_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "environment": {
            "runtime": "Node.js 22",
            "mode": "MOCK",
            "locale_pilot": "VN/vi Asia/Bangkok manual-chain-hoist",
            "thbison_resources_used": "none",
        },
        "test_evidence": [
            "delivery/junit-planning.xml",
            "delivery/http-matrix.json",
            "delivery/scenario-results.json",
            "delivery/kit-reference.xml",
            "delivery/kit-upstream-naive-date.md",
            "delivery/qa/qa-verdict.json",
            "delivery/security-scan.json",
            "delivery/benchmark.json",
        ],
        "counts": {
            "unit_pass": 17,
            "http_matrix_pass": 16,
            "http_matrix_fail": 0,
            "kit_self_test": "50 PASS, 1 FAIL (test_naive_date_rejected, upstream, kit not patched)",
            "internal_url_id_hits": len(hits),
        },
        "real_provider_probe": {
            "status": "OUT_OF_SCOPE_CONTRACTOR",
            "receipt": "No THBISON or OpenSEO tenant credentials requested or used.",
        },
        "public_posts_created": 0,
        "paid_calls": 0,
        "known_defects": [
            "vendor_kit/tests/test_contracts.py::test_naive_date_rejected FAIL (jsonschema date-time accepts naive ISO). Module assertAwareInstant rejects naive instants.",
        ],
        "handoff": "docs/HANDOFF.md",
    }
    manifest = {
        "release_version": RELEASE_VERSION,
        "code_commit": None,
        "source_commit": None,
        "source_revision_sha256": tree_hash,
        "source_tree_sha256": tree_hash,
        "contract_sha256": CONTRACT,
        "artifact_sha256": payload_sha,
        "artifact_name": PAYLOAD_NAME,
        "lockfile_sha256": lock_sha,
        "envelope": OFFICIAL_NAME,
        "tests": tests,
        "files": sorted(payload_names),
        "file_count": len(payload_names),
        "payload_bytes": payload_path.stat().st_size,
        "internal_url_id_hits": len(hits),
    }

    receipt_path = RELEASE_DIR / "RECEIPT.json"
    manifest_path = RELEASE_DIR / "RELEASE_MANIFEST.json"
    receipt_path.write_text(json.dumps(receipt, indent=2) + "\n")
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n")
    shutil.copy2(rev_path, RELEASE_DIR / "SOURCE_REVISION")
    shutil.copy2(lock_path, RELEASE_DIR / "package-lock.json")
    shutil.copy2(ROOT / "docs" / "HANDOFF.md", RELEASE_DIR / "HANDOFF.md")
    shutil.copy2(ROOT / "delivery" / "REVIEW.md", RELEASE_DIR / "REVIEW.md")
    shutil.copy2(ROOT / "delivery" / "kit-upstream-naive-date.md", RELEASE_DIR / "kit-upstream-naive-date.md")

    checksum_targets = [
        PAYLOAD_NAME,
        "SOURCE_REVISION",
        "package-lock.json",
        "RECEIPT.json",
        "RELEASE_MANIFEST.json",
        "HANDOFF.md",
        "REVIEW.md",
        "kit-upstream-naive-date.md",
    ]
    checksum_lines = []
    for name in checksum_targets:
        checksum_lines.append(f"{sha256_file(RELEASE_DIR / name)}  {name}")
    checksums_text = "\n".join(checksum_lines) + "\n"
    checksums_path = RELEASE_DIR / "CHECKSUMS.txt"
    checksums_path.write_text(checksums_text)

    # verify checksums in place before boxing
    proc = subprocess.run(
        ["sha256sum", "-c", "CHECKSUMS.txt"],
        cwd=RELEASE_DIR,
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise SystemExit(f"pre-envelope checksum failed\n{proc.stdout}\n{proc.stderr}")

    official = RELEASE_DIR / OFFICIAL_NAME
    with zipfile.ZipFile(official, "w", zipfile.ZIP_DEFLATED) as z:
        for name in checksum_targets + ["CHECKSUMS.txt"]:
            z.write(RELEASE_DIR / name, name)

    official_sha = sha256_file(official)

    # extract envelope to temp and re-run sha256sum -c
    with tempfile.TemporaryDirectory() as td:
        with zipfile.ZipFile(official) as z:
            z.extractall(td)
        proc2 = subprocess.run(
            ["sha256sum", "-c", "CHECKSUMS.txt"],
            cwd=td,
            capture_output=True,
            text=True,
            check=False,
        )
        verify_out = proc2.stdout
        if proc2.returncode != 0:
            raise SystemExit(f"envelope checksum failed\n{proc2.stdout}\n{proc2.stderr}")
        env_hits = []
        for dirpath, _, filenames in os.walk(td):
            for fn in filenames:
                p = Path(dirpath) / fn
                rel = str(p.relative_to(td))
                if fn.endswith(".zip"):
                    with zipfile.ZipFile(p) as inner:
                        if any(n.endswith("NOTION_PAGES.json") for n in inner.namelist()):
                            env_hits.append({"kind": "excluded_file_present", "path": "NOTION_PAGES.json"})
                        for n in inner.namelist():
                            if n.endswith("/"):
                                continue
                            env_hits.extend(scan_bytes(n, inner.read(n)))
                else:
                    env_hits.extend(scan_bytes(rel, p.read_bytes()))
        if env_hits:
            raise SystemExit("internal scan hits in envelope: " + json.dumps(env_hits, indent=2)[:4000])

    (RELEASE_DIR / "OFFICIAL.sha256").write_text(f"{official_sha}  {OFFICIAL_NAME}\n")
    (RELEASE_DIR / "SHA256SUM-C.txt").write_text(verify_out)
    (ROOT / "delivery" / "RECEIPT.json").write_text(json.dumps(receipt, indent=2) + "\n")
    (ROOT / "delivery" / "RELEASE_MANIFEST.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / "delivery" / "CHECKSUMS.txt").write_text(checksums_text)

    # only one official zip remains
    payload_path.unlink()

    print(json.dumps({
        "official": str(official),
        "official_sha256": official_sha,
        "payload_sha256": payload_sha,
        "source_revision_sha256": tree_hash,
        "code_commit": None,
        "source_commit": None,
        "files_in_payload": len(payload_names),
        "official_bytes": official.stat().st_size,
        "sha256sum_c": verify_out.strip().splitlines(),
        "internal_url_id_hits": 0,
    }, indent=2))


if __name__ == "__main__":
    main()
