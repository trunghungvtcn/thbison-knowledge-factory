import hashlib

import pytest

from kf_pilot.content_os_gateway import EvidenceMappingError, map_knowledge_output


def source(text="Verified synthetic quote"):
    return {
        "project_id": "test-thbison",
        "data_class": "TEST_ONLY",
        "knowledge_revision": "fixture-r1",
        "policy_version": "knowledge-policy-r1",
        "as_of": "2030-01-01T00:00:00Z",
        "claims": [{
            "claim_id": "claim-1",
            "text": text,
            "quote": text,
            "quote_sha256": hashlib.sha256(text.encode()).hexdigest(),
            "status": "ELIGIBLE",
            "risk": "DESCRIPTIVE",
            "provenance_verified": True,
            "source": {"id": "fixture-source", "revision": "1", "sha256": "a" * 64, "locator": "fixture://claim-1"},
        }],
    }


def test_maps_verified_fixture_with_identity_and_hashes():
    result = map_knowledge_output(source(), expected_project_id="test-thbison")
    assert result["data_class"] == "TEST_ONLY"
    assert result["claims"][0]["status"] == "ELIGIBLE"
    assert result["claims"][0]["allowed_uses"] == ["DRAFT"]
    assert len(result["snapshot_sha256"]) == 64


def test_missing_provenance_is_hold_not_eligible():
    payload = source()
    payload["claims"][0]["provenance_verified"] = False
    result = map_knowledge_output(payload, expected_project_id="test-thbison")
    assert result["claims"][0]["status"] == "HOLD"
    assert result["claims"][0]["allowed_uses"] == []
    assert "MISSING_OR_UNVERIFIED_PROVENANCE" in result["gaps"][0]


def test_human_hold_is_never_upgraded():
    payload = source()
    payload["claims"][0]["status"] = "HUMAN_HOLD"
    result = map_knowledge_output(payload, expected_project_id="test-thbison")
    assert result["claims"][0]["status"] == "HOLD"


def test_project_and_data_class_fail_closed():
    with pytest.raises(EvidenceMappingError, match="PROJECT_MISMATCH"):
        map_knowledge_output(source(), expected_project_id="other")
    payload = source()
    payload["data_class"] = "PRODUCTION"
    with pytest.raises(EvidenceMappingError, match="ONLY_TEST_ONLY"):
        map_knowledge_output(payload, expected_project_id="test-thbison")
