"""Vendor 1 planning simulator (REFERENCE / STUB). Actual V1 is MISSING."""

from __future__ import annotations

from typing import Any

from thbison_v6.contract_validate import assert_valid
from thbison_v6.faults import FaultPlan
from thbison_v6.hashutil import payload_digest
from thbison_v6.ledger import FileLedger

REQUIRED_BRIEF_FIELDS = (
    "contract_version",
    "project_id",
    "data_class",
    "brief_id",
    "brief_revision",
    "research_id",
    "scope",
    "title",
    "audience",
    "intent",
    "primary_keyword",
    "secondary_keywords",
    "questions",
    "outline",
    "evidence_requirements",
    "product_refs",
    "proposed_publish_at",
    "editorial_constraints",
    "origin",
)


class PlanningSimulator:
    vendor = "VENDOR_1"
    kind = "STUB"

    def __init__(self, ledger: FileLedger, faults: FaultPlan | None = None):
        self.ledger = ledger
        self.faults = faults or FaultPlan()

    def plan(self, request: dict[str, Any]) -> dict[str, Any]:
        project_id = request.get("project_id", "proj-lab")
        origin = "MANUAL" if request.get("origin") == "MANUAL" else "RESEARCH"
        scope = request.get("scope") or {
            "country_code": "VN",
            "language": "vi",
            "timezone": "Asia/Bangkok",
            "domain": "manual-chain-hoist",
        }
        product_refs = request.get("product_refs") or ["THB-PILOT"]
        brief = {
            "contract_version": "1.0.0",
            "project_id": project_id,
            "data_class": "TEST_ONLY",
            "brief_id": "brief-ref-001",
            "brief_revision": 1,
            "research_id": "research-ref-001",
            "scope": scope,
            "title": "Cau tao pa lang xich keo tay (TEST ONLY)",
            "audience": "operators",
            "intent": "informational",
            "primary_keyword": "pa lang xich keo tay",
            "secondary_keywords": [],
            "questions": ["What can be stated from the supplied source?"],
            "outline": ["Scope", "Source-supported description"],
            "evidence_requirements": [
                "Every factual block maps to allowed claim IDs."
            ],
            "product_refs": product_refs,
            "proposed_publish_at": None,
            "editorial_constraints": [
                "TEST ONLY: do not publish or treat synthetic facts as product evidence."
            ],
            "origin": origin,
        }
        assert_valid("ContentBrief", brief)
        output = {
            "research": None,
            "brief": brief,
        }
        # PlanningOutput.research is required in schema — emit synthetic research too
        research = {
            "contract_version": "1.0.0",
            "project_id": project_id,
            "data_class": "TEST_ONLY",
            "research_id": "research-ref-001",
            "request_id": "request-ref-001",
            "scope": scope,
            "keywords": [
                {
                    "keyword": brief["primary_keyword"],
                    "volume": None,
                    "difficulty": None,
                    "measurement_status": "SYNTHETIC",
                    "provider": "fake-seo",
                    "captured_at": "2030-01-01T00:00:00Z",
                    "source_ref": "synthetic-keywords",
                }
            ],
            "provider_snapshot": {
                "artifact_id": "test-keywords",
                "sha256": "aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa",
                "bytes": 100,
                "media_type": "application/json",
            },
            "warnings": ["SYNTHETIC; not measured SEO data."],
        }
        assert_valid("ResearchResult", research)
        planning = {"research": research, "brief": brief}
        assert_valid("PlanningOutput", planning)
        self.ledger.put("planning", brief["brief_id"], planning)
        return planning

    def revise(self, brief_id: str, patch: dict[str, Any]) -> dict[str, Any]:
        found = self.ledger.get("planning", brief_id)
        if not found:
            raise KeyError(brief_id)
        brief = dict(found["brief"])
        brief.update(patch)
        brief["brief_revision"] = int(brief.get("brief_revision", 1)) + 1
        assert_valid("ContentBrief", brief)
        found = dict(found)
        found["brief"] = brief
        self.ledger.put("planning", brief_id, found)
        return found
