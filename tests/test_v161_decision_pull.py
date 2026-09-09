import pytest

from kf_pilot.v16.decision_pull import DecisionPullError, LiveReviewSnapshot, bind_live_decision, plain_text


def snapshot(**changes):
    data = dict(
        page_id="page-1",
        legacy_id="KC-1",
        decision="APPROVED",
        reviewer_note="keep",
        status="Ready",
        reviewed_entity_id="entity-1",
        reviewed_version_id="version-1",
    )
    data.update(changes)
    return LiveReviewSnapshot(**data)


def test_safe_pull_binds_entity_and_version():
    binding = bind_live_decision(snapshot=snapshot(), mapped_page_id="page-1", claim_entity_id="entity-1")
    assert binding.reviewed_claim_version_id == "version-1"
    assert binding.notes == "keep"


def test_safe_pull_rejects_page_or_entity_mismatch():
    with pytest.raises(DecisionPullError):
        bind_live_decision(snapshot=snapshot(), mapped_page_id="other", claim_entity_id="entity-1")
    with pytest.raises(DecisionPullError):
        bind_live_decision(snapshot=snapshot(), mapped_page_id="page-1", claim_entity_id="entity-2")


def test_plain_text_reads_supported_notion_shapes():
    assert plain_text({"type": "select", "select": {"name": "APPROVED"}}) == "APPROVED"
    assert plain_text({"type": "rich_text", "rich_text": [{"plain_text": "note"}]}) == "note"
