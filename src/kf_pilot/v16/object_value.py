from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any


class ObjectValueValidationError(ValueError):
    pass


UNIT_CONVERSIONS: dict[str, tuple[str, Decimal]] = {
    "g": ("kg", Decimal("0.001")),
    "kg": ("kg", Decimal("1")),
    "t": ("kg", Decimal("1000")),
    "tonne": ("kg", Decimal("1000")),
    "lb": ("kg", Decimal("0.45359237")),
    "n": ("N", Decimal("1")),
    "kn": ("N", Decimal("1000")),
    "mm": ("mm", Decimal("1")),
    "cm": ("mm", Decimal("10")),
    "m": ("mm", Decimal("1000")),
    "day": ("day", Decimal("1")),
    "month": ("month", Decimal("1")),
    "year": ("year", Decimal("1")),
}
COMPARATORS = {"EQ", "NE", "GT", "GTE", "LT", "LTE"}


def _number(value: Any) -> int | float:
    if isinstance(value, bool):
        raise ObjectValueValidationError("boolean is not a numeric amount")
    try:
        decimal = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise ObjectValueValidationError(f"invalid numeric amount: {value!r}") from None
    if not decimal.is_finite():
        raise ObjectValueValidationError("amount must be finite")
    if decimal == decimal.to_integral():
        return int(decimal)
    return float(decimal.normalize())


def normalize_object_value(value: Any) -> tuple[dict[str, Any], list[str]]:
    """Normalize explicit structures; legacy prose is retained but blocks approval."""
    if not isinstance(value, dict):
        text = " ".join(str(value).split())
        if not text:
            raise ObjectValueValidationError("object_value is required")
        return {"type": "legacy_text", "value": text}, ["OBJECT_VALUE_UNSTRUCTURED"]

    kind = value.get("type")
    if kind == "quantity":
        allowed = {"type", "amount", "unit", "operator"}
        extra = set(value) - allowed
        if extra:
            raise ObjectValueValidationError(f"quantity has unknown fields: {sorted(extra)}")
        unit = str(value.get("unit", "")).strip().lower()
        if unit not in UNIT_CONVERSIONS:
            raise ObjectValueValidationError(f"unsupported unit: {unit!r}")
        operator = str(value.get("operator", "EQ")).upper()
        if operator not in COMPARATORS:
            raise ObjectValueValidationError(f"unsupported operator: {operator!r}")
        amount = Decimal(str(_number(value.get("amount"))))
        normalized_unit, factor = UNIT_CONVERSIONS[unit]
        return {
            "type": "quantity",
            "amount": _number(amount),
            "unit": unit,
            "operator": operator,
            "normalized_amount": _number(amount * factor),
            "normalized_unit": normalized_unit,
        }, []

    if kind == "enum":
        if set(value) - {"type", "value"}:
            raise ObjectValueValidationError("enum contains unknown fields")
        item = " ".join(str(value.get("value", "")).split()).upper()
        if not item:
            raise ObjectValueValidationError("enum value is required")
        return {"type": "enum", "value": item}, []

    if kind == "boolean":
        if set(value) - {"type", "value"} or not isinstance(value.get("value"), bool):
            raise ObjectValueValidationError("boolean requires only a boolean value")
        return {"type": "boolean", "value": value["value"]}, []

    raise ObjectValueValidationError(f"unsupported object_value type: {kind!r}")
