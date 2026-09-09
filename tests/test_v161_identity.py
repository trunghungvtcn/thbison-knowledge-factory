from kf_pilot.v16.condition_ast import canonicalize_ast
from kf_pilot.v16.identity import claim_version_id, semantic_hash, stable_entity_id_from_legacy


def base_payload():
    return {
        "product_family": "MANUAL_CHAIN_HOIST",
        "subject": "MANUAL_CHAIN_HOIST",
        "predicate": "INSPECTION_INTERVAL",
        "object_value": "CONDITION_DEPENDENT",
        "applicability": "JURISDICTION_SPECIFIC",
        "jurisdiction": "VN",
        "condition_ast": {
            "op": "OR",
            "args": [
                {"op": "COMPARE", "field": "environment", "comparator": "EQ", "value": "OUTDOOR"},
                {"op": "COMPARE", "field": "use_mode", "comparator": "EQ", "value": "MOBILE"}
            ]
        },
        "exception_ast": {"op": "FALSE"},
    }


def test_entity_id_is_deterministic():
    assert stable_entity_id_from_legacy("KC-001") == stable_entity_id_from_legacy("KC-001")


def test_condition_order_does_not_change_version():
    left = base_payload()
    right = base_payload()
    right["condition_ast"]["args"].reverse()
    assert claim_version_id("entity-1", left) == claim_version_id("entity-1", right)


def test_and_to_or_changes_version_but_not_entity():
    before = base_payload()
    after = base_payload()
    after["condition_ast"]["op"] = "AND"
    assert claim_version_id("entity-1", before) != claim_version_id("entity-1", after)
    assert stable_entity_id_from_legacy("KC-001") == stable_entity_id_from_legacy("KC-001")


def test_canonical_text_does_not_affect_semantic_version():
    payload = base_payload()
    with_text = dict(payload, canonical_text="Một cách viết khác")
    assert claim_version_id("entity-1", payload) == claim_version_id("entity-1", with_text)


def test_same_semantics_can_be_shared_but_version_ownership_is_distinct():
    payload = base_payload()
    assert semantic_hash(payload) == semantic_hash(dict(payload))
    assert claim_version_id("entity-1", payload) != claim_version_id("entity-2", payload)
