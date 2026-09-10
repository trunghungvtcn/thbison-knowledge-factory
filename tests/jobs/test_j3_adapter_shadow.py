"""Integration tests against real contractor public packages. No importorskip."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest

from j3_support import PIN_KW, contract, require_contractor

require_contractor()

from grok_notion_projection import FakeTransport  # noqa: E402

from kf_pilot.contractor_bridge.adapter import (  # noqa: E402
    LocalShadowAdapter,
    mark_allowed,
)


def test_shadow_run_calls_real_ledger_and_fake_transport(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text('{"fixture":"J3"}\n', encoding="utf-8")
    transport = mark_allowed(
        FakeTransport(allowed_targets={"sandbox-page-001"}, token="local-shadow-token")
    )
    adapter = LocalShadowAdapter(tmp_path / "work", transport=transport, **PIN_KW)
    result = adapter.run(contract(repo, snapshot), snapshot)
    assert result.status == "LOCAL_SHADOW_COMPLETE"
    assert result.production_writes is False
    assert result.live_notion is False
    assert result.envelopes["admit"]["status"] == "ok"
    assert result.envelopes["reserve"]["status"] == "ok"
    assert result.envelopes["attempt"]["status"] == "ok"
    assert result.envelopes["finalize"]["status"] == "ok"
    assert result.envelopes["project"]["status"] == "ok"
    assert result.evidence["pins"]["j1_commit_sha"] == PIN_KW["j1_commit_sha"]
    assert result.evidence["pins"]["j1_input_hash"] == PIN_KW["j1_input_hash"]
    assert result.evidence["pins"]["j1_input_verified"] is False
    adapter.close()


def test_replay_reads_terminal_state(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text('{"fixture":"J3-replay"}\n', encoding="utf-8")
    adapter = LocalShadowAdapter(tmp_path / "work", **PIN_KW)
    spec = contract(repo, snapshot)
    first = adapter.run(spec, snapshot)
    second = adapter.run(spec, snapshot)
    assert first.status == "LOCAL_SHADOW_COMPLETE"
    assert second.status == "DUPLICATE_NOOP"
    assert second.reason_code == "IDEMPOTENT_HIT"
    assert second.evidence["ledger_state"] == "SUCCEEDED"
    assert second.contractor_job_id == first.contractor_job_id
    adapter.close()


def test_hash_mismatch_fail_closed(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text("safe", encoding="utf-8")
    adapter = LocalShadowAdapter(tmp_path / "work", **PIN_KW)
    with pytest.raises(Exception, match="hash mismatch"):
        adapter.run(contract(repo, snapshot, input_manifest_sha256="0" * 64), snapshot)
    adapter.close()


def test_unmarked_transport_rejected_before_project(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text('{"fixture":"deny"}\n', encoding="utf-8")

    class Unmarked:
        def call(self, *args, **kwargs):  # pragma: no cover
            raise AssertionError("project must not be reached")

    adapter = LocalShadowAdapter(tmp_path / "work", transport=Unmarked(), **PIN_KW)
    result = adapter.run(contract(repo, snapshot), snapshot)
    assert result.status == "FAILED"
    assert result.reason_code == "TRANSPORT_NOT_ALLOWED"
    assert "project" not in result.envelopes
    assert result.envelopes["finalize"]["status"] == "ok"
    adapter.close()
