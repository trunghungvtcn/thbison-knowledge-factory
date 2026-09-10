from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, FormatChecker
from referencing import Registry, Resource

ROOT = Path(__file__).resolve().parents[2]
SCHEMAS = ROOT / "contracts" / "schemas"


@lru_cache(maxsize=1)
def _registry() -> Registry:
    resources = []
    for p in SCHEMAS.glob("*.json"):
        contents = json.loads(p.read_text(encoding="utf-8"))
        resources.append((p.name, Resource.from_contents(contents)))
    return Registry().with_resources(resources)


@lru_cache(maxsize=None)
def load_schema(name: str) -> dict:
    return json.loads((SCHEMAS / f"{name}.json").read_text(encoding="utf-8"))


def validate_payload(name: str, payload: dict[str, Any]) -> list[str]:
    schema = load_schema(name)
    validator = Draft202012Validator(
        schema,
        format_checker=FormatChecker(),
        registry=_registry(),
    )
    return [f"{list(e.absolute_path)}: {e.message}" for e in validator.iter_errors(payload)]


def assert_valid(name: str, payload: dict[str, Any]) -> None:
    errors = validate_payload(name, payload)
    if errors:
        raise ValueError(f"CONTRACT_INVALID:{name}:" + ";".join(errors))
