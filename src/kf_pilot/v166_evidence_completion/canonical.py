import hashlib
import json
import os
from pathlib import Path


class ContractError(ValueError):
    pass


def require(condition, code, detail=""):
    if not condition:
        raise ContractError(code + ((":" + detail) if detail else ""))


def _pairs(pairs):
    out = {}
    for key, value in pairs:
        require(key not in out, "DUPLICATE_JSON_KEY", key)
        out[key] = value
    return out


def loads(raw):
    return json.loads(raw, object_pairs_hook=_pairs)


def load(path):
    return loads(Path(path).read_text(encoding="utf-8"))


def rows(path):
    raw = Path(path).read_text(encoding="utf-8")
    decoder = json.JSONDecoder(object_pairs_hook=_pairs)
    result, index = [], 0
    while index < len(raw):
        while index < len(raw) and raw[index].isspace():
            index += 1
        if index < len(raw):
            value, index = decoder.raw_decode(raw, index)
            result.append(value)
    return result


def bytes_for(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def digest(value):
    return hashlib.sha256(bytes_for(value)).hexdigest()


def sha256(raw):
    return hashlib.sha256(raw).hexdigest()


def exact(value, keys, name="OBJECT"):
    require(type(value) is dict, "TYPE_MISMATCH", name)
    require(set(value) == set(keys), "KEY_SET_MISMATCH", name)


def confined(root, value):
    require(type(value) is str and value and "\x00" not in value, "INVALID_PATH")
    # Treat both separators as path syntax on every runner.  Without this
    # normalization, POSIX interprets a Windows traversal such as ``..\\x``
    # as a harmless filename and the contract becomes platform-dependent.
    normalized = value.replace("\\", "/")
    require(".." not in Path(normalized).parts, "PATH_TRAVERSAL")
    root = Path(root).resolve()
    candidate = Path(normalized)
    if not candidate.is_absolute():
        candidate = root / candidate
    resolved = candidate.resolve()
    require(os.path.commonpath([str(root), str(resolved)]) == str(root), "PATH_TRAVERSAL")
    return resolved
