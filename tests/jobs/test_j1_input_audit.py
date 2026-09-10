from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "jobs" / "j1_input_audit.py"
JOBS = ROOT / "scripts" / "jobs"
if str(JOBS) not in sys.path:
    sys.path.insert(0, str(JOBS))
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from j1_input_audit import file_status, record, strict_exit_code  # noqa: E402

WATCHED = [
    ROOT / "manifests" / "migration_assets.json",
    ROOT / "sample_input" / "resource_manifest.csv",
    ROOT / "sample_input" / "files" / "sample-kito-cb010.html",
    ROOT / "fixtures" / "v161" / "legacy_rows.json",
    ROOT / "src" / "kf_pilot" / "legacy_manifest.py",
    ROOT / "v162" / "baseline-reproduced" / "notion_typed_update_plan.json",
]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _run(
    out: Path,
    missing: Path | None = None,
    *,
    strict: bool = False,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--root", str(ROOT), "--out", str(out)]
    if missing is not None:
        cmd.extend(["--missing-out", str(missing)])
    if strict:
        cmd.append("--strict")
    return subprocess.run(cmd, cwd=ROOT, check=check, capture_output=True, text=True)


def test_file_status_splits_present_from_hash_verified() -> None:
    assert file_status(exists=True, actual_sha256="abc") == "PRESENT"
    assert file_status(exists=True, expected_sha256="aa", actual_sha256="aa") == "HASH_VERIFIED"
    assert file_status(exists=True, expected_sha256="aa", actual_sha256="bb") == "HASH_MISMATCH"
    assert file_status(exists=False, expected_sha256="aa") == "MISSING"
    assert (
        file_status(exists=False, expected_sha256="aa", absent="MISSING_EXTERNAL")
        == "MISSING_EXTERNAL"
    )
    present = record(path="x", status="PRESENT", provenance="SOURCE", source="t", actual_sha256="abc")
    verified = record(
        path="y",
        status="HASH_VERIFIED",
        provenance="SOURCE",
        source="t",
        expected_sha256="aa",
        actual_sha256="aa",
    )
    assert present["present"] is True and present["hash_verified"] is False
    assert verified["present"] is True and verified["hash_verified"] is True


def test_strict_exit_code_missing_and_mismatch() -> None:
    missing = [{"status": "MISSING"}]
    mismatch = [{"status": "HASH_MISMATCH"}]
    blocked = [{"status": "BLOCKED_INPUT"}]
    clean = [{"status": "PRESENT"}, {"status": "HASH_VERIFIED"}]
    assert strict_exit_code(missing) != 0
    assert strict_exit_code(mismatch) != 0
    assert strict_exit_code(blocked) != 0
    assert strict_exit_code(clean) == 0


def test_j1_audit_is_read_only_and_idempotent(tmp_path: Path) -> None:
    before = {path: _sha(path) for path in WATCHED if path.is_file()}
    first = tmp_path / "a.json"
    second = tmp_path / "b.json"
    missing = tmp_path / "missing.json"
    one = _run(first, missing)
    two = _run(second)
    after = {path: _sha(path) for path in before}
    assert after == before
    report_a = json.loads(first.read_text(encoding="utf-8"))
    report_b = json.loads(second.read_text(encoding="utf-8"))
    assert report_a["inputs_mutated"] is False
    assert report_a["read_only"] is True
    assert report_a["inventory_sha256"] == report_b["inventory_sha256"]
    stderr = json.loads(one.stderr.strip().splitlines()[-1])
    assert report_a["inventory_sha256"] == stderr["inventory_sha256"]
    assert stderr["exit_code"] == 0
    assert stderr["mode"] == "inventory"
    assert missing.is_file()
    git = subprocess.run(
        ["git", "status", "--porcelain", "--", "manifests", "sample_input", "fixtures", "src", "v162"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    assert git.stdout.strip() == ""


def test_j1_cross_checks_runtime_and_reports_gaps(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    _run(out)
    report = json.loads(out.read_text(encoding="utf-8"))
    by_path: dict[str, list] = {}
    for item in report["inventory"]:
        by_path.setdefault(item["path"], []).append(item)

    for rel in (
        "v162/baseline-reproduced/notion_typed_update_plan.json",
        "sample_input/files/sample-kito-cb010.html",
        "fixtures/v161/legacy_rows.json",
        "src/kf_pilot/legacy_manifest.py",
    ):
        runtime = [item for item in by_path[rel] if item.get("runtime_required")]
        assert runtime, rel
        assert runtime[0]["status"] == "PRESENT", rel
        assert runtime[0]["present"] is True
        assert runtime[0]["hash_verified"] is False
        assert runtime[0]["actual_sha256"]

    verified = [
        item
        for item in report["inventory"]
        if item["status"] == "HASH_VERIFIED" and item["source"] == "manifests/migration_assets.json"
    ]
    assert verified, "matching GitHub migrated_sha256 must be HASH_VERIFIED"
    assert all(item["present"] and item["hash_verified"] for item in verified)

    ps1 = "vendor/v162-deployment-pack/scripts/run_pack_smoke.ps1"
    github_ps1 = [
        item
        for item in by_path[ps1]
        if item["source"] == "manifests/migration_assets.json" and item["status"] == "HASH_MISMATCH"
    ]
    assert github_ps1, "expected GitHub migrated_sha256 mismatch for pack smoke ps1"
    assert github_ps1[0]["present"] is True
    assert github_ps1[0]["hash_verified"] is False

    external = [item for item in report["missing_or_mismatch"] if item["status"] == "MISSING_EXTERNAL"]
    locators = {item["path"] for item in external}
    assert any("kaggle-kernel-outputs-20260909.zip" in path for path in locators)
    assert any("kf-pilot-input.zip" in path for path in locators)
    assert any("manual_decisions-v2-reviewed.csv" in path or "manual_decisions.csv" in path for path in locators)
    assert all(
        item.get("publish_to_github") is False
        for item in external
        if item["provenance"] == "REAL_INPUT_EXTERNAL"
    )
    assert all(item.get("blocked_input") is True for item in external)

    provenances = {item["provenance"] for item in report["inventory"]}
    assert {"SIMULATED", "HISTORICAL_ARTIFACT", "REAL_INPUT_EXTERNAL", "SOURCE"} <= provenances

    nested_mismatch = [
        item
        for item in report["missing_or_mismatch"]
        if item["status"] == "HASH_MISMATCH" and "v162_input_manifest.json" in item["source"]
    ]
    assert nested_mismatch, "historical Windows locators must be resolved and hash-checked"

    summary = report["summary"]
    assert summary["runtime_required_count"] >= 14
    assert summary["hash_mismatch_count"] >= 1
    assert summary["missing_count"] >= 5
    assert "OK" not in summary["status_counts"]


def test_j1_publishes_three_hashes_and_reproduction(tmp_path: Path) -> None:
    out = tmp_path / "report.json"
    proc = _run(out)
    report = json.loads(out.read_text(encoding="utf-8"))
    hashes = report["hashes"]
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    tool = _sha(SCRIPT)
    assert hashes["audited_source_sha"] == head
    assert hashes["tool_sha"] == tool
    assert hashes["inventory_content_hash"] == report["inventory_sha256"]
    names = {row["name"]: row["command"] for row in hashes["reproduction"]}
    assert names["audited_source_sha"] == "git rev-parse HEAD"
    assert "sha256sum" in names["tool_sha"]
    assert "scripts/jobs/j1_input_audit.py" in names["tool_sha"]
    assert "inventory_sha256" in names["inventory_content_hash"] or "canonical_dumps" in names["inventory_content_hash"]
    stderr = json.loads(proc.stderr.strip().splitlines()[-1])
    assert stderr["hashes"]["audited_source_sha"] == head
    assert stderr["hashes"]["tool_sha"] == tool
    assert stderr["hashes"]["inventory_content_hash"] == report["inventory_sha256"]


def test_j1_strict_exits_nonzero_on_missing_or_mismatch(tmp_path: Path) -> None:
    before = {path: _sha(path) for path in WATCHED if path.is_file()}
    out = tmp_path / "strict.json"
    proc = _run(out, strict=True, check=False)
    assert proc.returncode != 0
    report = json.loads(out.read_text(encoding="utf-8"))
    stderr = json.loads(proc.stderr.strip().splitlines()[-1])
    assert stderr["mode"] == "strict"
    assert stderr["exit_code"] == proc.returncode
    assert report["summary"]["missing_count"] >= 1
    assert report["summary"]["hash_mismatch_count"] >= 1
    assert report["summary"]["strict_would_fail"] is True
    # inventory still written; recovered bytes untouched
    after = {path: _sha(path) for path in WATCHED if path.is_file()}
    assert after == before
