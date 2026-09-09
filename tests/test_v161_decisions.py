import pytest

from kf_pilot.v16.decisions import DecisionBinding, build_notion_update, effective_decision


def test_approval_is_stale_after_version_change():
    binding = DecisionBinding("APPROVED", "cv_old", "keep me")
    assert effective_decision(
        system_status="REVIEW_REQUIRED",
        current_claim_version_id="cv_new",
        binding=binding,
        condition_unresolved=False,
    ) == "STALE_REVIEW"


def test_hold_overrides_approval():
    binding = DecisionBinding("APPROVED", "cv_current")
    assert effective_decision(
        system_status="HOLD",
        current_claim_version_id="cv_current",
        binding=binding,
        condition_unresolved=False,
    ) == "BLOCKED_BY_SYSTEM_STATUS"


def test_unresolved_condition_blocks_approval():
    binding = DecisionBinding("APPROVED", "cv_current")
    assert effective_decision(
        system_status="REVIEW_REQUIRED",
        current_claim_version_id="cv_current",
        binding=binding,
        condition_unresolved=True,
    ) == "HOLD_CONDITION_REVIEW"


def test_notion_update_rejects_human_fields():
    with pytest.raises(ValueError):
        build_notion_update({"Decision": "APPROVED"})
    assert build_notion_update({"Claim Version ID": "cv_1"}) == {"Claim Version ID": "cv_1"}
