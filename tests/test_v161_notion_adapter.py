import pytest

from kf_pilot.v16.notion_adapter import NotionAdapterError, notion_schema_diff, typed_system_properties


def test_schema_diff_adds_v16_fields_without_renaming_current_fields():
    report = notion_schema_diff({"Knowledge ID": "rich_text", "Claim Text": "rich_text"})
    additions = {item["name"] for item in report["additions"]}
    assert "Claim Entity ID" in additions
    assert "Reviewed Version ID" in additions
    assert report["type_mismatches"] == []


def test_typed_adapter_rejects_human_owned_fields():
    with pytest.raises(NotionAdapterError, match="human-owned"):
        typed_system_properties({"decision": "APPROVED"})


def test_long_ast_fails_instead_of_truncating():
    with pytest.raises(NotionAdapterError, match="2000"):
        typed_system_properties({"condition_ast": "x" * 2001})
