from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class GateError(ValueError):
    def __init__(self, code: str, detail: str = ""):
        self.code = code
        super().__init__(f"{code}: {detail}" if detail else code)


def require(ok: bool, code: str, detail: str = "") -> None:
    if not ok:
        raise GateError(code, detail)


def exact_keys(value: Any, required: set[str], optional: set[str] = frozenset()) -> None:
    require(isinstance(value, dict), "OBJECT_REQUIRED")
    require(required <= value.keys(), "MISSING_FIELDS", str(sorted(required - value.keys())))
    require(value.keys() <= required | optional, "UNKNOWN_FIELDS",
            str(sorted(value.keys() - required - optional)))


def nonempty(value: Any) -> bool:
    return isinstance(value, str) and bool(value.strip())


def canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
                      allow_nan=False).encode("utf-8")


def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def digest(value: Any) -> str:
    return sha256(canonical_bytes(value))


def unique_index(rows: list[dict], key: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        require(nonempty(row.get(key)), "MISSING_ID", key)
        require(row[key] not in result, "DUPLICATE_ID", f"{key}={row[key]}")
        result[row[key]] = row
    return result


def confined_path(root: Path, relative: str) -> Path:
    require(nonempty(relative) and not Path(relative).is_absolute(), "INVALID_SOURCE_PATH")
    target = (root / relative).resolve()
    require(target.is_relative_to(root.resolve()), "SOURCE_PATH_ESCAPE")
    require(target.is_file(), "SOURCE_UNAVAILABLE", relative)
    return target


def load_json(path: Path) -> Any:
    def pairs(items):
        out = {}
        for key, value in items:
            require(key not in out, "DUPLICATE_JSON_KEY", key)
            out[key] = value
        return out
    def nonfinite(value):
        raise GateError("NONFINITE_JSON_NUMBER", value)
    return json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=pairs,
                      parse_constant=nonfinite)


