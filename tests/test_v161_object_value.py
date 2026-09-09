import pytest

from kf_pilot.v16.object_value import ObjectValueValidationError, normalize_object_value


def test_quantity_is_normalized_to_base_unit():
    value, issues = normalize_object_value({"type": "quantity", "amount": 1.5, "unit": "t", "operator": "LTE"})
    assert value["normalized_amount"] == 1500
    assert value["normalized_unit"] == "kg"
    assert issues == []


def test_legacy_text_is_retained_but_flagged():
    value, issues = normalize_object_value("not more than rated load")
    assert value["type"] == "legacy_text"
    assert issues == ["OBJECT_VALUE_UNSTRUCTURED"]


def test_unknown_quantity_field_fails():
    with pytest.raises(ObjectValueValidationError):
        normalize_object_value({"type": "quantity", "amount": 1, "unit": "t", "guess": True})
