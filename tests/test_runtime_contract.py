from __future__ import annotations

from dataclasses import replace
from pathlib import Path
import hashlib
import subprocess

import pytest

from kf_pilot.runtime_contract import ContractError, RunContract, execute_test_only


def contract(repo: Path, snapshot: Path, **changes) -> RunContract:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True,
        capture_output=True, text=True,
    ).stdout.strip()
    base = RunContract(
        job_id="MCH-CONTRACT-SMOKE-001",
        task_type="VALIDATE_SCORE",
        domain="manual-chain-hoist",
        repository="trunghungvtcn/thbison-knowledge-factory",
        code_commit=commit,
        dataset_snapshot_id="TEST_ONLY-fixture-v1",
        input_manifest_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        mode="TEST_ONLY",
        allowed_outputs=("run-report.json", "submission-ledger.json"),
        attempt_budget=1,
        timeout_seconds=30,
    )
    return replace(base, **changes)


def test_contract_round_trip_and_duplicate(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text('{"fixture":"TEST_ONLY"}\n', encoding="utf-8")
    spec = contract(repo, snapshot)
    first = execute_test_only(spec, repo, snapshot, tmp_path / "out")
    second = execute_test_only(spec, repo, snapshot, tmp_path / "out")
    assert first["status"] == "TEST_ONLY_COMPLETE"
    assert first["production_writes"] is False
    assert second["status"] == "DUPLICATE_NOOP"


def test_rejects_wrong_hash(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text("safe", encoding="utf-8")
    with pytest.raises(ContractError, match="hash mismatch"):
        execute_test_only(contract(repo, snapshot, input_manifest_sha256="0" * 64), repo, snapshot, tmp_path / "out")


def test_rejects_wrong_commit(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text("safe", encoding="utf-8")
    with pytest.raises(ContractError, match="commit mismatch"):
        execute_test_only(contract(repo, snapshot, code_commit="0" * 40), repo, snapshot, tmp_path / "out")


def test_rejects_invalid_timeout(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[1]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text("safe", encoding="utf-8")
    with pytest.raises(ContractError, match="timeout_seconds"):
        contract(repo, snapshot, timeout_seconds=0).validate()

