from kf_pilot.v16.migration import LegacyCanonicalRow, migrate_row


def sample_row(**changes):
    data = {
        "legacy_canonical_id": "KC-001",
        "canonical_text": "Guidance",
        "predicate": "INSPECTION_INTERVAL",
        "object_value": {"type": "enum", "value": "CONDITION_DEPENDENT"},
        "condition_tags": ["OUTDOOR", "MOBILE_USE"],
        "condition_raw_text": "outdoor or mobile",
        "system_status": "REVIEW_REQUIRED",
        "decision": "PENDING",
        "notes": "human note",
        "notion_page_id": "page-1",
    }
    data.update(changes)
    return LegacyCanonicalRow.model_validate(data)


def test_replay_keeps_ids_and_page_mapping():
    first = migrate_row(sample_row(), "RUN-A")
    replay = migrate_row(sample_row(), "RUN-B")
    assert first.entity["claim_entity_id"] == replay.entity["claim_entity_id"]
    assert first.version["claim_version_id"] == replay.version["claim_version_id"]
    assert first.publication_mapping == replay.publication_mapping
    assert replay.decision_binding["notes"] == "human note"


def test_parser_fix_creates_version_not_entity():
    before = migrate_row(sample_row(), "RUN-A")
    fixed = sample_row(
        parsed_condition_ast={
            "op": "OR",
            "args": [
                {"op": "COMPARE", "field": "environment", "comparator": "EQ", "value": "OUTDOOR"},
                {"op": "COMPARE", "field": "use_mode", "comparator": "EQ", "value": "MOBILE"},
            ],
        }
    )
    fixed_result = migrate_row(fixed, "RUN-C")
    assert before.entity["claim_entity_id"] == fixed_result.entity["claim_entity_id"]
    assert before.version["claim_version_id"] != fixed_result.version["claim_version_id"]


def test_unresolved_condition_creates_blocking_issue():
    result = migrate_row(sample_row(decision="APPROVED"), "RUN-A")
    assert result.version["condition_unresolved"] is True
    assert result.issues[0]["blocking"] is True
    assert result.decision_binding["effective_decision"] == "HOLD_CONDITION_REVIEW"


def test_legacy_approval_without_version_binding_is_stale():
    result = migrate_row(
        sample_row(condition_tags=[], condition_raw_text=None, decision="APPROVED", system_status="REVIEW_REQUIRED"),
        "RUN-A",
    )
    assert result.decision_binding["reviewed_claim_version_id"] is None
    assert result.decision_binding["effective_decision"] == "STALE_REVIEW"


def test_approval_bound_to_current_version_remains_effective():
    pending = migrate_row(sample_row(condition_tags=[], condition_raw_text=None), "RUN-A")
    reviewed = sample_row(
        condition_tags=[],
        condition_raw_text=None,
        decision="APPROVED",
        reviewed_claim_version_id=pending.version["claim_version_id"],
    )
    result = migrate_row(reviewed, "RUN-B")
    assert result.decision_binding["effective_decision"] == "APPROVED"
