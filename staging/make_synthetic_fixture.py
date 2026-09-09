from __future__ import annotations

import json
from pathlib import Path

OUT = Path(__file__).with_name("synthetic_staging_plan.json")


def rich(text: str):
    return {"rich_text": [{"type": "text", "text": {"content": text}}]}


def sel(name: str):
    return {"select": {"name": name}}


records = [
    {
        "operation": "UPDATE",
        "environment": "STAGING",
        "synthetic": True,
        "synthetic_id": "V161-STAGING-SYNTH-001",
        "target_ref": "STAGING_FIXTURE_PAGE_001",
        "properties": {
            "Claim Text": rich("V16.1 synthetic staging quantity record"),
            "Run ID": rich("V16.1-STAGING-SYNTH"),
            "Condition Status": sel("RESOLVED"),
            "System Status": sel("REVIEW_REQUIRED"),
        },
        "semantic_fixture": {
            "object_value": {"type": "quantity", "amount": 1, "unit": "kN"},
            "condition_ast": {"op": "TRUE"},
        },
    },
    {
        "operation": "UPDATE",
        "environment": "STAGING",
        "synthetic": True,
        "synthetic_id": "V161-STAGING-SYNTH-002",
        "target_ref": "STAGING_FIXTURE_PAGE_002",
        "properties": {
            "Claim Text": rich("V16.1 synthetic staging enum record"),
            "Run ID": rich("V16.1-STAGING-SYNTH"),
            "Condition Status": sel("RESOLVED"),
            "System Status": sel("REVIEW_REQUIRED"),
        },
        "semantic_fixture": {
            "object_value": {"type": "enum", "value": "TEST_ONLY"},
            "condition_ast": {"op": "TRUE"},
        },
    },
    {
        "operation": "UPDATE",
        "environment": "STAGING",
        "synthetic": True,
        "synthetic_id": "V161-STAGING-SYNTH-003",
        "target_ref": "STAGING_FIXTURE_PAGE_003",
        "properties": {
            "Claim Text": rich("V16.1 synthetic staging boolean record"),
            "Run ID": rich("V16.1-STAGING-SYNTH"),
            "Condition Status": sel("RESOLVED"),
            "System Status": sel("REVIEW_REQUIRED"),
        },
        "semantic_fixture": {
            "object_value": {"type": "boolean", "value": True},
            "condition_ast": {"op": "TRUE"},
        },
    },
]

OUT.write_text(json.dumps({"target_kind": "DEDICATED_STAGING", "records": records}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(OUT)
