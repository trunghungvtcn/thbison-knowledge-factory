from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "jobs" / "j1_input_audit.py"
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


def _run(out: Path, missing: Path | None = None) -> subprocess.CompletedProcess[str]:
    cmd = [sys.executable, str(SCRIPT), "--root", str(ROOT), "--out", str(out)]
    if missing is not None:
        cmd.extend(["--missing-out", str(missing)])
    return subprocess.run(cmd, cwd=ROOT, check=True, capture_output=True, text=True)


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
    assert report_a["inventory_sha256"] == json.loads(one.stderr.strip().splitlines()[-1])["inventory_sha256"]
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
    by_path = {}
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
        assert runtime[0]["status"] == "OK", rel
        assert runtime[0]["actual_sha256"]

    ps1 = "vendor/v162-deployment-pack/scripts/run_pack_smoke.ps1"
    github_ps1 = [
        item
        for item in by_path[ps1]
        if item["source"] == "manifests/migration_assets.json" and item["status"] == "HASH_MISMATCH"
    ]
    assert github_ps1, "expected GitHub migrated_sha256 mismatch for pack smoke ps1"

    external = [item for item in report["missing_or_mismatch"] if item["status"] == "MISSING_EXTERNAL"]
    locators = {item["path"] for item in external}
    assert any("kaggle-kernel-outputs-20260909.zip" in path for path in locators)
    assert any("kf-pilot-input.zip" in path for path in locators)
    assert any("manual_decisions-v2-reviewed.csv" in path or "manual_decisions.csv" in path for path in locators)
    assert all(item.get("publish_to_github") is False for item in external if item["provenance"] == "REAL_INPUT_EXTERNAL")

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
