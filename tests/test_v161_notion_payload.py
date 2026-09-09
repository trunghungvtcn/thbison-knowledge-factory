from kf_pilot.v16.notion_payload import build_update_only_plan


def test_plan_is_update_only_and_excludes_human_properties():
    versions = [
        {
            "claim_entity_id": "entity-1",
            "claim_version_id": "version-1",
            "legacy_canonical_id": "KC-1",
            "canonical_text": "Do not overload.",
            "condition_unresolved": False,
            "object_value_structured": True,
            "semantic_payload": {
                "predicate": "RATED_LOAD_LIMIT",
                "condition_ast": {"op": "TRUE"},
                "applicability": "GENERIC",
                "jurisdiction": None,
            },
        }
    ]
    mappings = [{"claim_entity_id": "entity-1", "remote_page_id": "page-1"}]
    plan = build_update_only_plan(versions, mappings, run_id="RUN-1")
    assert plan["mode"] == "NO_WRITE"
    assert plan["created_count"] == 0
    assert plan["updated_count"] == 1
    assert plan["operations"][0]["operation"] == "UPDATE"
    assert "Decision" not in plan["operations"][0]["typed_properties"]
    assert "Reviewer Note" not in plan["operations"][0]["typed_properties"]
    assert plan["operations"][0]["typed_properties"]["Claim Entity ID"]["rich_text"]


def test_missing_mapping_never_falls_back_to_create():
    versions = [
        {
            "claim_entity_id": "unmapped",
            "claim_version_id": "version-1",
            "legacy_canonical_id": "KC-1",
            "canonical_text": "Text",
            "condition_unresolved": False,
            "semantic_payload": {
                "predicate": "P",
                "condition_ast": {"op": "TRUE"},
                "applicability": "GENERIC",
                "jurisdiction": None,
            },
        }
    ]
    plan = build_update_only_plan(versions, [], run_id="RUN-1")
    assert plan["created_count"] == 0
    assert plan["updated_count"] == 0
    assert plan["missing_mapping_count"] == 1


def test_mapping_collisions_fail_closed():
    mappings = [
        {"claim_entity_id": "entity-1", "remote_page_id": "page-1"},
        {"claim_entity_id": "entity-2", "remote_page_id": "page-1"},
    ]
    import pytest

    with pytest.raises(ValueError, match="page maps to multiple entities"):
        build_update_only_plan([], mappings, run_id="RUN-1")


def test_existing_hold_is_preserved_in_logical_plan():
    versions = [
        {
            "claim_entity_id": "entity-1",
            "claim_version_id": "version-1",
            "legacy_canonical_id": "KC-1",
            "canonical_text": "Text",
            "condition_unresolved": False,
            "object_value_structured": True,
            "semantic_payload": {"condition_ast": {"op": "TRUE"}, "applicability": "GENERIC"},
        }
    ]
    mappings = [{"claim_entity_id": "entity-1", "remote_page_id": "page-1"}]
    bindings = [{"claim_entity_id": "entity-1", "effective_decision": "BLOCKED_BY_SYSTEM_STATUS"}]
    plan = build_update_only_plan(versions, mappings, run_id="RUN-1", bindings=bindings)
    assert plan["operations"][0]["logical_properties"]["system_status"] == "HOLD"
