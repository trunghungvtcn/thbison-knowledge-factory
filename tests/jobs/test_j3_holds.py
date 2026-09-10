from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from j3_support import contract, require_contractor

require_contractor()

from kf_pilot.contractor_bridge.adapter import LocalShadowAdapter  # noqa: E402


def test_missing_j1_j2_pins_are_human_hold(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text('{"fixture":"hold"}\n', encoding="utf-8")
    adapter = LocalShadowAdapter(tmp_path / "work")
    result = adapter.run(contract(repo, snapshot), snapshot)
    assert result.status == "HUMAN_HOLD"
    assert result.reason_code == "BLOCKED_INPUT"
    joined = " ".join(result.hold_reasons)
    assert "J1_COMMIT_SHA_MISSING" in joined
    assert "J1_INPUT_HASH_MISSING" in joined
    assert "J2_COMMIT_SHA_MISSING" in joined
    assert "J2_INPUT_HASH_MISSING" in joined
    assert result.production_writes is False
    adapter.close()


def test_commit_shaped_string_is_not_input_hash(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    snapshot = tmp_path / "fixture.json"
    snapshot.write_text('{"fixture":"shape"}\n', encoding="utf-8")
    adapter = LocalShadowAdapter(
        tmp_path / "work",
        j1_input_sha="a" * 40,
        j2_env_sha="b" * 40,
    )
    result = adapter.run(contract(repo, snapshot), snapshot)
    assert result.status == "HUMAN_HOLD"
    assert any("J1_INPUT_HASH_MISSING" in h for h in result.hold_reasons)
    assert any("J2_INPUT_HASH_MISSING" in h for h in result.hold_reasons)
    adapter.close()
