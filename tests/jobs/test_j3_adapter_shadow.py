"""Integration tests that import contractor packages for real.

Transport is FakeTransport from grok_notion_projection, not a mocked module.
"""

from __future__ import annotations

from dataclasses import replace
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
pytest.importorskip("grok_asset_store")
pytest.importorskip("grok_locator")
pytest.importorskip("grok_notion_projection")

from grok_notion_projection import FakeTransport  # noqa: E402

from kf_pilot.contractor_bridge.adapter import LocalShadowAdapter  # noqa: E402


def _contract(repo: Path, snapshot: Path, **changes) -> RunContract:
    commit = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    if len(commit) != 40:
        commit = "3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b"
    base = RunContract(
        job_id="J3-SHADOW-001",
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
    return replace(base, **changes) if changes else base


def test_shadow_run_calls_real_ledger_and_fake_transport(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text('{"fixture":"J3"}\n', encoding="utf-8")
    transport = FakeTransport(allowed_targets={"sandbox-page-001"}, token="local-shadow-token")
    adapter = LocalShadowAdapter(
        tmp_path / "work",
        transport=transport,
        j1_input_sha="a" * 40,
        j2_env_sha="b" * 40,
    )
    result = adapter.run(_contract(repo, snapshot), snapshot)
    assert result.status == "LOCAL_SHADOW_COMPLETE"
    assert result.production_writes is False
    assert result.live_notion is False
    assert result.envelopes["admit"]["status"] == "ok"
    assert result.envelopes["freeze"]["status"] == "ok"
    assert result.envelopes["resolve"]["status"] == "ok"
    assert result.envelopes["finalize"]["reason_code"] == "OK"
    assert result.envelopes["project"]["status"] == "ok"
    assert transport.calls, "FakeTransport must have recorded projection.apply"
    assert transport.calls[0]["op"] == "projection.apply"
    assert type(adapter.ledger).__name__ == "JobLedger"
    adapter.close()


def test_replay_is_idempotent_hit(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text('{"fixture":"J3-replay"}\n', encoding="utf-8")
    adapter = LocalShadowAdapter(
        tmp_path / "work",
        j1_input_sha="a" * 40,
        j2_env_sha="b" * 40,
    )
    spec = _contract(repo, snapshot)
    first = adapter.run(spec, snapshot)
    second = adapter.run(spec, snapshot)
    assert first.status == "LOCAL_SHADOW_COMPLETE"
    assert second.status == "DUPLICATE_NOOP"
    assert second.reason_code == "IDEMPOTENT_HIT"
    assert second.contractor_job_id == first.contractor_job_id
    adapter.close()


def test_hash_mismatch_fail_closed(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text("safe", encoding="utf-8")
    adapter = LocalShadowAdapter(tmp_path / "work", j1_input_sha="a" * 40, j2_env_sha="b" * 40)
    with pytest.raises(Exception, match="hash mismatch"):
        adapter.run(_contract(repo, snapshot, input_manifest_sha256="0" * 64), snapshot)
    adapter.close()
