import pytest
from thbison_v6.contract_validate import assert_valid, validate_payload
from thbison_v6.harness.lab import Lab


def test_additional_properties_rejected():
    brief = Lab().planning.plan({"project_id": "proj-lab"})["brief"]
    bad = dict(brief)
    bad["sneaky"] = True
    assert validate_payload("ContentBrief", bad)


def test_wrong_scope_type_rejected():
    brief = Lab().planning.plan({"project_id": "proj-lab"})["brief"]
    bad = dict(brief)
    bad["scope"] = "PILOT"
    assert validate_payload("ContentBrief", bad)


def test_receipt_drafted_status_rejected():
    rec = Lab().run_reference_chain()["receipt"]
    bad = dict(rec)
    bad["status"] = "DRAFTED"
    assert validate_payload("PublicationReceipt", bad)


def test_missing_contract_version_rejected():
    brief = Lab().planning.plan({"project_id": "proj-lab"})["brief"]
    bad = dict(brief)
    del bad["contract_version"]
    with pytest.raises(ValueError, match="CONTRACT_INVALID"):
        assert_valid("ContentBrief", bad)


def test_chain_does_not_strip_to_hide_errors(tmp_path):
    chain = Lab(root=tmp_path).run_reference_chain()
    # full objects still have required fields; not reduced subsets
    assert "contract_version" in chain["brief"]
    assert "claims" in chain["bundle"]
    assert "blocks" in chain["article"]
