"""INTERNAL-BRIDGE-01: remaining fail-closed defects. Real contractor package. No importorskip."""

from __future__ import annotations

from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))

from j3_support import contract, require_contractor

require_contractor()

from grok_notion_projection import FakeTransport  # noqa: E402

from kf_pilot.contractor_bridge.adapter import LocalShadowAdapter  # noqa: E402
from kf_pilot.contractor_bridge.pins import (  # noqa: E402
    J1_INVENTORY_COMMIT,
    J1_PUBLISHED_INVENTORY_DIGEST,
    J2_ENV_COMMIT,
    J2_JUNIT_SHA256,
    transport_is_allowed,
)

SYNTHETIC_PINS = {
    "j1_commit_sha": J1_INVENTORY_COMMIT,
    "j1_input_hash": "1" * 64,
    "j2_commit_sha": J2_ENV_COMMIT,
    "j2_input_hash": "2" * 64,
}

PUBLISHED_UNVERIFIED_PINS = {
    "j1_commit_sha": J1_INVENTORY_COMMIT,
    "j1_input_hash": J1_PUBLISHED_INVENTORY_DIGEST,
    "j2_commit_sha": J2_ENV_COMMIT,
    "j2_input_hash": J2_JUNIT_SHA256,
}


def _spec(repo: Path, tmp_path: Path, name: str = "fixture.json", payload: str = '{"fixture":"INTERNAL-BRIDGE-01"}'):
    snapshot = tmp_path / name
    snapshot.write_text(payload + "\n", encoding="utf-8")
    spec = contract(
        repo,
        snapshot,
        job_id="INTERNAL-BRIDGE-01",
        dataset_snapshot_id="TEST_ONLY-SYNTHETIC-internal-bridge-01",
    )
    return spec, snapshot


def _transport() -> FakeTransport:
    return FakeTransport(allowed_targets={"sandbox-page-001"}, token="local-shadow-token")


def test_b1_missing_pins_hold_before_freeze_admit_project(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "missing.json")
    adapter = LocalShadowAdapter(tmp_path / "work")
    result = adapter.run(spec, snapshot)
    assert result.status == "HUMAN_HOLD"
    assert result.reason_code == "BLOCKED_INPUT"
    joined = " ".join(result.hold_reasons)
    assert "J1_COMMIT_SHA_MISSING" in joined
    assert "J1_INPUT_HASH_MISSING" in joined
    assert "J2_COMMIT_SHA_MISSING" in joined
    assert "J2_INPUT_HASH_MISSING" in joined
    assert "freeze" not in result.envelopes
    assert "admit" not in result.envelopes
    assert "project" not in result.envelopes
    assert not (tmp_path / "work" / "cas").exists()
    assert result.evidence.get("blocked_before") == ["freeze", "admit", "project"]
    adapter.close()


def test_b1_malformed_pin_holds_before_freeze(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "malformed.json")
    adapter = LocalShadowAdapter(
        tmp_path / "work",
        j1_commit_sha="not-a-sha",
        j1_input_hash="1" * 64,
        j2_commit_sha=J2_ENV_COMMIT,
        j2_input_hash="2" * 64,
    )
    result = adapter.run(spec, snapshot)
    assert result.status == "HUMAN_HOLD"
    assert result.reason_code == "BLOCKED_INPUT"
    assert any("J1_COMMIT_SHA_MALFORMED" in h for h in result.hold_reasons)
    assert "freeze" not in result.envelopes
    assert "admit" not in result.envelopes
    assert "project" not in result.envelopes
    assert not (tmp_path / "work" / "cas").exists()
    adapter.close()


def test_b3_self_flagged_transport_rejected_zero_calls(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "flagged.json")

    class Flagged:
        LOCAL_SHADOW_ALLOWED = True

        def __init__(self) -> None:
            self.calls: list[object] = []

        def call(self, *args: object, **kwargs: object) -> None:
            self.calls.append((args, kwargs))
            raise AssertionError("transport must not be called")

    flagged = Flagged()
    adapter = LocalShadowAdapter(tmp_path / "work", transport=flagged, **SYNTHETIC_PINS)
    result = adapter.run(spec, snapshot)
    assert result.status == "FAILED"
    assert result.reason_code == "TRANSPORT_NOT_ALLOWED"
    assert flagged.calls == []
    assert "project" not in result.envelopes
    adapter.close()


def test_b3_subclass_even_with_flag_rejected_zero_calls(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "subclass.json")

    class SubFake(FakeTransport):
        pass

    sneaky = SubFake(allowed_targets={"sandbox-page-001"}, token="local-shadow-token")
    sneaky.LOCAL_SHADOW_ALLOWED = True  # type: ignore[attr-defined]
    assert transport_is_allowed(sneaky) is False
    adapter = LocalShadowAdapter(tmp_path / "work", transport=sneaky, **SYNTHETIC_PINS)
    result = adapter.run(spec, snapshot)
    assert result.status == "FAILED"
    assert result.reason_code == "TRANSPORT_NOT_ALLOWED"
    assert sneaky.calls == []
    assert "project" not in result.envelopes
    adapter.close()


def test_b3_exact_fake_transport_without_flag_is_allowed(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "exact.json")
    transport = _transport()
    assert getattr(transport, "LOCAL_SHADOW_ALLOWED", None) is not True
    assert transport_is_allowed(transport) is True
    adapter = LocalShadowAdapter(tmp_path / "work", transport=transport, **SYNTHETIC_PINS)
    result = adapter.run(spec, snapshot)
    assert result.status == "LOCAL_SHADOW_COMPLETE"
    assert result.evidence["real_data_pass"] is False
    assert result.evidence["synthetic_fixture"] is True
    assert result.evidence["hash_verified"] is False
    assert result.evidence["pins"]["j1_input_verified"] is False
    assert len(transport.calls) >= 1
    adapter.close()


def test_b2_projection_fail_after_succeeded_replay_is_not_duplicate_noop(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "boom.json", '{"fixture":"b2-fail"}')
    transport = _transport()
    adapter = LocalShadowAdapter(tmp_path / "work", transport=transport, **SYNTHETIC_PINS)

    class Boom:
        def project(self, *args: object, **kwargs: object) -> dict[str, str]:
            return {"status": "error", "reason_code": "INJECTED_PROJECT_FAIL"}

    real = adapter.projector
    adapter.projector = Boom()  # type: ignore[assignment]
    first = adapter.run(spec, snapshot)
    assert first.status == "FAILED"
    assert first.reason_code == "INJECTED_PROJECT_FAIL"
    assert first.envelopes["finalize"]["status"] == "ok"
    assert "receipt" not in first.evidence
    ledger = adapter.ledger.get(first.contractor_job_id)
    assert ledger.get("state") == "SUCCEEDED"
    assert ledger.get("projection_status") != "APPLIED"

    adapter.projector = real
    calls_before = len(transport.calls)
    second = adapter.run(spec, snapshot)
    assert second.status == "LOCAL_SHADOW_COMPLETE"
    assert second.reason_code != "IDEMPOTENT_HIT"
    assert second.status != "DUPLICATE_NOOP"
    assert second.evidence.get("resumed") is True
    assert second.evidence.get("projection_complete") is True
    assert second.envelopes["project"]["status"] == "ok"
    assert len(transport.calls) > calls_before

    calls_after_resume = len(transport.calls)
    third = adapter.run(spec, snapshot)
    assert third.status == "DUPLICATE_NOOP"
    assert third.reason_code == "IDEMPOTENT_HIT"
    assert third.evidence.get("projection_complete") is True
    assert third.contractor_job_id == first.contractor_job_id
    assert len(transport.calls) == calls_after_resume
    adapter.close()


def test_b2_crash_before_receipt_replay_not_false_success(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "crash.json", '{"fixture":"b2-crash"}')
    transport = _transport()
    adapter = LocalShadowAdapter(tmp_path / "work", transport=transport, **SYNTHETIC_PINS)

    class Crash:
        def project(self, *args: object, **kwargs: object) -> dict[str, str]:
            raise RuntimeError("crash before receipt")

    adapter.projector = Crash()  # type: ignore[assignment]
    first = adapter.run(spec, snapshot)
    assert first.status == "FAILED"
    assert first.reason_code == "PROJECT_CRASH"
    assert not (tmp_path / "work" / "shadow-receipt.json").exists()

    adapter.projector = __import__("grok_notion_projection", fromlist=["Projector"]).Projector()
    second = adapter.run(spec, snapshot)
    assert second.status != "DUPLICATE_NOOP"
    assert second.status == "LOCAL_SHADOW_COMPLETE"
    assert second.evidence.get("resumed") is True
    adapter.close()


def test_b2_resume_denied_transport_is_reconcile_required(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "deny-resume.json")

    class Flagged:
        LOCAL_SHADOW_ALLOWED = True

        def __init__(self) -> None:
            self.calls: list[object] = []

        def call(self, *args: object, **kwargs: object) -> None:
            self.calls.append((args, kwargs))
            raise AssertionError("transport must not be called")

    flagged = Flagged()
    adapter = LocalShadowAdapter(tmp_path / "work", transport=flagged, **SYNTHETIC_PINS)
    first = adapter.run(spec, snapshot)
    assert first.status == "FAILED"
    assert first.reason_code == "TRANSPORT_NOT_ALLOWED"
    assert flagged.calls == []
    second = adapter.run(spec, snapshot)
    assert second.status == "RECONCILE_REQUIRED"
    assert second.reason_code == "TRANSPORT_NOT_ALLOWED"
    assert flagged.calls == []
    adapter.close()


def test_envelope_fail_closed_skips_project(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "reserve.json")
    transport = _transport()
    adapter = LocalShadowAdapter(tmp_path / "work", transport=transport, **SYNTHETIC_PINS)

    def boom_reserve(*args: object, **kwargs: object) -> dict[str, str]:
        return {"status": "error", "reason_code": "INJECTED_RESERVE_FAIL"}

    adapter.ledger.reserve_budget = boom_reserve  # type: ignore[method-assign]
    result = adapter.run(spec, snapshot)
    assert result.status == "FAILED"
    assert result.reason_code == "INJECTED_RESERVE_FAIL"
    assert result.status != "LOCAL_SHADOW_COMPLETE"
    assert "project" not in result.envelopes
    assert transport.calls == []
    adapter.close()


def test_digest_change_does_not_reuse_old_result(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "digest.json", '{"fixture":"digest"}')
    work = tmp_path / "work"
    t1 = _transport()
    a1 = LocalShadowAdapter(work, transport=t1, **SYNTHETIC_PINS)
    first = a1.run(spec, snapshot)
    assert first.status == "LOCAL_SHADOW_COMPLETE"
    changed = dict(SYNTHETIC_PINS)
    changed["j2_commit_sha"] = "a" * 40
    t2 = _transport()
    a2 = LocalShadowAdapter(work, transport=t2, **changed)
    second = a2.run(spec, snapshot)
    assert second.status != "DUPLICATE_NOOP"
    assert second.status != "LOCAL_SHADOW_COMPLETE"
    assert second.reason_code == "DIGEST_CONFLICT"
    a1.close()
    a2.close()


def test_b4_roles_split_and_published_hash_not_upgraded(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "b4.json")
    transport = _transport()
    adapter = LocalShadowAdapter(tmp_path / "work", transport=transport, **PUBLISHED_UNVERIFIED_PINS)
    result = adapter.run(spec, snapshot)
    pins = result.evidence["pins"]
    assert pins["pin_roles"]["code_commit"] == "j1_commit_sha"
    assert pins["pin_roles"]["environment"] == "j2_commit_sha"
    assert pins["pin_roles"]["input_hash"] == "j1_input_hash"
    assert pins["j2_role"] == "environment"
    assert pins["j2_env_commit_known"] is True
    assert pins["j1_input_verified"] is False
    assert pins["j2_input_verified"] is False
    assert pins["hash_verified"] is False
    assert pins["j1_hash_status"] == "PUBLISHED_UNVERIFIED"
    assert pins["j2_hash_status"] == "ENVIRONMENT_UNVERIFIED"
    assert result.evidence["real_data_pass"] is False
    assert result.evidence["hash_verified"] is False
    assert "HASH_VERIFIED" not in pins["j1_hash_status"]
    adapter.close()


def test_b4_synthetic_complete_is_not_real_data_pass(tmp_path: Path) -> None:
    repo = Path(__file__).resolve().parents[2]
    spec, snapshot = _spec(repo, tmp_path, "synth.json")
    adapter = LocalShadowAdapter(tmp_path / "work", transport=_transport(), **SYNTHETIC_PINS)
    result = adapter.run(spec, snapshot)
    assert result.status == "LOCAL_SHADOW_COMPLETE"
    assert result.evidence["synthetic_fixture"] is True
    assert result.evidence["synthetic_pass"] is True
    assert result.evidence["real_data_pass"] is False
    assert result.evidence["pins"]["j1_hash_status"] == "SYNTHETIC"
    assert spec.mode == "TEST_ONLY"
    assert "SYNTHETIC" in spec.dataset_snapshot_id
    adapter.close()
