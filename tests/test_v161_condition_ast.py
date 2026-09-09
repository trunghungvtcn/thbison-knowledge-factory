import pytest

from kf_pilot.v16.condition_ast import (
    ConditionValidationError,
    canonicalize_ast,
    contains_unresolved,
    migrate_legacy_tags,
)


def leaf(field: str, value: str):
    return {"op": "COMPARE", "field": field, "comparator": "EQ", "value": value}


def test_and_or_child_order_is_canonical():
    a, b = leaf("environment", "OUTDOOR"), leaf("use_mode", "MOBILE")
    assert canonicalize_ast({"op": "OR", "args": [a, b]}) == canonicalize_ast(
        {"op": "OR", "args": [b, a]}
    )


def test_and_and_or_remain_distinct():
    a, b = leaf("environment", "OUTDOOR"), leaf("use_mode", "MOBILE")
    assert canonicalize_ast({"op": "AND", "args": [a, b]}) != canonicalize_ast(
        {"op": "OR", "args": [a, b]}
    )


def test_legacy_multi_tags_are_not_guessed():
    ast = migrate_legacy_tags(["OUTDOOR", "MOBILE_USE"])
    assert ast["op"] == "UNRESOLVED"
    assert contains_unresolved(ast)


def test_double_not_is_simplified():
    original = leaf("environment", "OUTDOOR")
    assert canonicalize_ast({"op": "NOT", "arg": {"op": "NOT", "arg": original}}) == canonicalize_ast(original)


def test_invalid_boolean_node_fails():
    with pytest.raises(ConditionValidationError):
        canonicalize_ast({"op": "OR", "args": [leaf("x", "y")]})


def test_unknown_fields_fail_closed():
    with pytest.raises(ConditionValidationError, match="unknown fields"):
        canonicalize_ast({"op": "COMPARE", "field": "x", "comparator": "EQ", "value": 1, "guess": True})


def test_unknown_raw_condition_is_unresolved():
    ast = migrate_legacy_tags([], "only when used outdoors")
    assert ast["op"] == "UNRESOLVED"
