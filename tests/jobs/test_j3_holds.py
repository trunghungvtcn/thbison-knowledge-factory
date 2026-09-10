from __future__ import annotations

from pathlib import Path
import hashlib
import os
import subprocess
import sys

import pytest

from kf_pilot.runtime_contract import RunContract


def _ensure_contractor_path() -> None:
    root = os.environ.get("CONTRACTOR_ROOT")
    if not root:
        candidate = Path("/tmp/j3/contractor")
        if candidate.is_dir():
            root = str(candidate)
    if not root:
        return
    for name in ("m1_locator", "m2_asset_store", "m3_job_ledger", "m4_notion_projection"):
        src = str(Path(root) / name / "src")
        if src not in sys.path:
            sys.path.insert(0, src)


_ensure_contractor_path()
pytest.importorskip("grok_job_ledger")

from kf_pilot.contractor_bridge.adapter import LocalShadowAdapter  # noqa: E402


def test_missing_j1_j2_pins_are_human_hold(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text('{"fixture":"hold"}\n', encoding="utf-8")
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=repo, check=True, capture_output=True, text=True
    ).stdout.strip()
    if len(commit) != 40:
        commit = "3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b"
    spec = RunContract(
        job_id="J3-HOLD-001",
        task_type="VALIDATE_SCORE",
        domain="manual-chain-hoist",
        repository="trunghungvtcn/thbison-knowledge-factory",
        code_commit=commit,
        dataset_snapshot_id="TEST_ONLY-j3-fixture",
        input_manifest_sha256=hashlib.sha256(snapshot.read_bytes()).hexdigest(),
        mode="TEST_ONLY",
        allowed_outputs=("shadow-receipt.json",),
        attempt_budget=1,
        timeout_seconds=30,
    )
    adapter = LocalShadowAdapter(tmp_path / "work")
    result = adapter.run(spec, snapshot)
    assert result.status == "HUMAN_HOLD"
    assert result.reason_code == "BLOCKED_INPUT"
    assert any("J1_INPUT_SHA" in h for h in result.hold_reasons)
    assert any("J2_ENV_SHA" in h for h in result.hold_reasons)
    assert result.production_writes is False
    adapter.close()
