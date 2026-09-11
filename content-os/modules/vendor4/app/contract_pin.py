from __future__ import annotations

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = ROOT / "contracts" / "shared" / "CONTRACT_SHA256.txt"


class ContractPinError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def load_contract_pin(path: Path | None = None) -> str:
    p = path or PIN_PATH
    if not p.is_file():
        raise ContractPinError("CONTRACT_PIN_MISSING", f"missing pin file: {p}")
    digest = p.read_text(encoding="utf-8").strip().split()[0].lower()
    if len(digest) != 64 or any(c not in "0123456789abcdef" for c in digest):
        raise ContractPinError("CONTRACT_PIN_INVALID", "pin is not sha256 hex")
    if digest == "0" * 64:
        raise ContractPinError("CONTRACT_PIN_INVALID", "zero digest is not a pin")
    override = os.getenv("CONTRACT_SHA256_OVERRIDE")
    if override and override.lower() != digest:
        raise ContractPinError("CONTRACT_PIN_MISMATCH", "override does not match packaged pin")
    return digest
