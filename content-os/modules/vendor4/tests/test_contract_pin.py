from pathlib import Path

import pytest

from app.contract_pin import ContractPinError, load_contract_pin

ROOT = Path(__file__).resolve().parents[1]


def test_packaged_pin_loads():
    digest = load_contract_pin()
    assert len(digest) == 64
    assert digest != "0" * 64


def test_missing_pin(tmp_path):
    with pytest.raises(ContractPinError) as ei:
        load_contract_pin(tmp_path / "missing.txt")
    assert ei.value.code == "CONTRACT_PIN_MISSING"


def test_zero_pin(tmp_path):
    p = tmp_path / "CONTRACT_SHA256.txt"
    p.write_text("0" * 64)
    with pytest.raises(ContractPinError) as ei:
        load_contract_pin(p)
    assert ei.value.code == "CONTRACT_PIN_INVALID"


def test_override_mismatch(monkeypatch):
    monkeypatch.setenv("CONTRACT_SHA256_OVERRIDE", "ab" * 32)
    with pytest.raises(ContractPinError) as ei:
        load_contract_pin()
    assert ei.value.code == "CONTRACT_PIN_MISMATCH"
