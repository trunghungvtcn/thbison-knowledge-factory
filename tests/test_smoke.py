from pathlib import Path
import unittest
from unittest.mock import patch

import pandas as pd

from kf_pilot.claims import (
    apply_product_consistency_gates,
    build_evidence_chunks,
    load_alias_registry,
    load_unit_registry,
    template_candidates,
    validate_candidates,
)
from kf_pilot.canonicalize import canonicalize_knowledge, normalize_claims
from kf_pilot.core import extract_resource, load_yaml, safe_resolve, validate_manifest
from kf_pilot.knowledge import knowledge_candidates, validate_knowledge
from kf_pilot.notion_sync import (
    NOTION_VERSION,
    candidate_properties,
    sync_candidates,
    sync_knowledge_items,
)


ROOT = Path(__file__).resolve().parents[1]


class PilotSmokeTest(unittest.TestCase):
    def test_cross_source_product_conflict_is_held(self):
        frame = pd.DataFrame([
            {"subject_entity_id": "kito-cb010", "predicate": "hand_chain_pull", "normalized_unit": "N", "normalized_value": 284.0, "reason_codes": [], "decision_state": "REVIEW_REQUIRED"},
            {"subject_entity_id": "kito-cb010", "predicate": "hand_chain_pull", "normalized_unit": "N", "normalized_value": 290.0, "reason_codes": [], "decision_state": "REVIEW_REQUIRED"},
        ])
        gated = apply_product_consistency_gates(frame)
        self.assertEqual(set(gated["decision_state"]), {"HOLD"})
        self.assertTrue(all("CROSS_SOURCE_CONFLICT" in reasons for reasons in gated["reason_codes"]))

    def test_standard_identifier_is_not_mistaken_for_product_model(self):
        evidence = pd.DataFrame([{
            "evidence_id": "e-vn-1", "resource_id": "vn-qtkd13", "resource_version_hash": "h",
            "publisher_id": "vn", "publisher_name": "Công báo Chính phủ Việt Nam", "original_url": "https://example.vn",
            "source_role": "REGULATION", "authority_tier": "PRIMARY_LEGAL", "jurisdiction": "VN",
            "applicability_scope": "MANUAL_CHAIN_HOIST_CAPACITY_GTE_1000_KG",
            "claim_families": "REGULATORY_REQUIREMENT", "legal_status": "CURRENT",
            "raw_text": "Thử động theo TCVN 4244 với tải trọng thử bằng 110% Q(tk).", "extraction_confidence": 0.99,
        }])
        validated = validate_knowledge(knowledge_candidates(evidence), evidence)
        self.assertEqual(set(validated["decision_state"]), {"REVIEW_REQUIRED"})

    def test_authority_source_creates_grounded_knowledge_not_product_specs(self):
        evidence = pd.DataFrame(
            [{
                "evidence_id": "e-authority-1",
                "resource_id": "osha-chain-falls",
                "resource_version_hash": "hash-1",
                "publisher_id": "publisher-us-osha",
                "publisher_name": "US OSHA",
                "original_url": "https://www.osha.gov/example",
                "source_role": "REGULATOR_GUIDANCE",
                "authority_tier": "GOVERNMENT_GUIDANCE",
                "jurisdiction": "US",
                "applicability_scope": "SHIPYARD_CHAIN_FALLS_AND_PULL_LIFTS",
                "claim_families": "REGULATORY_REQUIREMENT|SAFETY_GUIDANCE",
                "legal_status": "CURRENT_AT_FETCH",
                "raw_text": "Chain falls and pull-lifts capacity must be clearly marked. Capacity must not be exceeded.",
                "extraction_confidence": 0.99,
            }]
        )
        candidates = knowledge_candidates(evidence)
        validated = validate_knowledge(candidates, evidence)
        self.assertEqual(set(validated["predicate"]), {"rated_capacity_marking", "overload_prohibition"})
        self.assertEqual(set(validated["decision_state"]), {"REVIEW_REQUIRED"})
        self.assertTrue(all(value == "KNOWLEDGE_ITEM" for value in validated["target_type"]))

    def test_semantic_variation_is_grounded_and_review_required(self):
        evidence = pd.DataFrame([{
            "evidence_id": "e-semantic-1", "resource_id": "authority-1", "resource_version_hash": "h",
            "publisher_id": "authority", "publisher_name": "Authority", "original_url": "https://example.gov/rule",
            "source_role": "REGULATOR_GUIDANCE", "authority_tier": "GOVERNMENT_GUIDANCE", "jurisdiction": "VN",
            "applicability_scope": "MANUAL_CHAIN_HOIST", "claim_families": "SAFETY_GUIDANCE",
            "legal_status": "CURRENT", "raw_text": "Không được nâng người bằng thiết bị pa lăng trong quá trình vận hành.",
            "extraction_confidence": 0.97,
        }])
        validated = validate_knowledge(knowledge_candidates(evidence), evidence)
        self.assertIn("people_lifting_prohibition", set(validated["predicate"]))
        self.assertEqual(set(validated["decision_state"]), {"REVIEW_REQUIRED"})

    def test_canonicalization_merges_equivalent_variants_and_keeps_evidence(self):
        base = {
            "claim_family": "REGULATORY_REQUIREMENT", "subject_product_family": "manual hand chain hoist",
            "predicate": "inspection_interval", "jurisdiction": "VN", "applicability_scope": "FIXED_COVERED",
            "legal_status": "CURRENT", "applicability_directness": "DIRECT", "authority_tier": "PRIMARY_LEGAL",
            "final_confidence": 99, "decision_state": "REVIEW_REQUIRED", "original_url": "https://example.gov/rule",
        }
        frame = pd.DataFrame([
            {**base, "candidate_id": "v1", "claim_text": "Thời hạn kiểm định định kỳ 3 năm.", "evidence_ids": ["e1"], "resource_id": "r1"},
            {**base, "candidate_id": "v2", "claim_text": "Chu kỳ kiểm định là ba năm.", "evidence_ids": ["e2"], "resource_id": "r2"},
        ])
        variants, canonical, relations, conflicts = canonicalize_knowledge(frame)
        self.assertEqual(len(variants), 2)
        self.assertEqual(len(canonical), 1)
        self.assertEqual(int(canonical.iloc[0]["evidence_count"]), 2)
        self.assertIn("EQUIVALENT", set(relations["relation"]))
        self.assertEqual(len(conflicts), 0)

    def test_canonicalization_holds_numeric_conflicts_in_same_scope(self):
        base = {
            "claim_family": "REGULATORY_REQUIREMENT", "subject_product_family": "manual hand chain hoist",
            "predicate": "inspection_interval", "jurisdiction": "VN", "applicability_scope": "FIXED_COVERED",
            "legal_status": "CURRENT", "applicability_directness": "DIRECT", "authority_tier": "PRIMARY_LEGAL",
            "final_confidence": 99, "decision_state": "REVIEW_REQUIRED", "original_url": "https://example.gov/rule",
        }
        frame = pd.DataFrame([
            {**base, "candidate_id": "v1", "claim_text": "Thời hạn kiểm định định kỳ 3 năm.", "evidence_ids": ["e1"], "resource_id": "r1"},
            {**base, "candidate_id": "v2", "claim_text": "Thời hạn kiểm định định kỳ 1 năm.", "evidence_ids": ["e2"], "resource_id": "r2"},
        ])
        _, canonical, relations, conflicts = canonicalize_knowledge(frame)
        self.assertEqual(len(conflicts), 1)
        self.assertIn("CONTRADICTS", set(relations["relation"]))
        self.assertEqual(set(canonical["decision_state"]), {"HOLD"})

    def test_vietnamese_thousands_and_calendar_dates_are_not_misread(self):
        frame = pd.DataFrame([
            {"candidate_id": "capacity", "claim_text": "Pa lăng có tải trọng từ 1.000 kg trở lên."},
            {"candidate_id": "date", "claim_text": "Ban hành ngày 28 tháng 12 năm 2016."},
        ])
        normalized = normalize_claims(frame).set_index("candidate_id")
        self.assertIn('"capacity_kg":1000.0', normalized.loc["capacity", "numeric_slots_json"])
        self.assertEqual(normalized.loc["date", "numeric_slots_json"], "{}")

    def test_table_cells_are_bundled_for_llm_context(self):
        frame = pd.DataFrame(
            [
                {"evidence_id": "e1", "resource_id": "r1", "page_no": 1, "table_id": "T1", "row_key": "0", "column_key": "0", "block_id": "", "raw_text": "Model", "extraction_confidence": 0.99, "mapping_confidence": 0.95},
                {"evidence_id": "e2", "resource_id": "r1", "page_no": 1, "table_id": "T1", "row_key": "1", "column_key": "0", "block_id": "", "raw_text": "CB010", "extraction_confidence": 0.98, "mapping_confidence": 0.94},
                {"evidence_id": "e3", "resource_id": "r1", "page_no": 1, "table_id": "T1", "row_key": "1", "column_key": "1", "block_id": "", "raw_text": "284 N", "extraction_confidence": 0.97, "mapping_confidence": 0.93},
            ]
        )
        chunks = build_evidence_chunks(frame)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks.iloc[0]["evidence_ids"], ["e1", "e2", "e3"])
        self.assertIn("CB010\n284 N", chunks.iloc[0]["raw_text"])

    def test_controlled_fixture(self):
        manifest = pd.read_csv(ROOT / "sample_input" / "resource_manifest.csv", keep_default_na=False)
        validation = validate_manifest(manifest, ROOT / "sample_input" / "files")
        self.assertEqual(validation.rejected, [])
        self.assertEqual(len(validation.accepted), 1)

        config = load_yaml(ROOT / "config" / "pilot_config.yaml")
        rows, _ = extract_resource(validation.accepted.to_dict(orient="records")[0], config)
        evidence = pd.DataFrame(rows)
        aliases = load_alias_registry(ROOT / "config" / "entity_aliases.csv")
        units = load_unit_registry(ROOT / "config" / "unit_registry.csv")
        candidates = template_candidates(evidence, aliases=aliases)
        validated = validate_candidates(
            candidates,
            evidence,
            aliases,
            units,
            {"rated_load", "standard_lift", "hand_chain_pull", "net_mass"},
        )
        self.assertEqual(len(validated), 3)
        self.assertEqual(set(validated["decision_state"]), {"REVIEW_REQUIRED"})
        self.assertTrue(all(not reasons for reasons in validated["reason_codes"]))

    def test_path_traversal_is_blocked(self):
        with self.assertRaises(ValueError):
            safe_resolve(ROOT / "sample_input" / "files", "../../outside.txt")

    def test_notion_payload_and_api_version(self):
        self.assertEqual(NOTION_VERSION, "2026-03-11")
        properties = candidate_properties(
            {
                "candidate_id": "candidate-1",
                "model_alias": "CB010",
                "predicate": "hand_chain_pull",
                "raw_value": "284",
                "raw_unit": "N",
                "final_confidence": 96,
                "risk_class": "CRITICAL_NUMERIC",
                "decision_state": "REVIEW_REQUIRED",
                "quote": "KITO CB010 hand chain pull: 284 N.",
            },
            "Pa lăng xích kéo tay",
            "run-1",
        )
        self.assertEqual(properties["Decision"]["select"]["name"], "PENDING")
        self.assertEqual(properties["Candidate ID"]["rich_text"][0]["text"]["content"], "candidate-1")

    def test_notion_resync_preserves_human_decision(self):
        candidates = pd.DataFrame(
            [
                {
                    "candidate_id": "candidate-1",
                    "model_alias": "CB010",
                    "predicate": "hand_chain_pull",
                    "raw_value": "284",
                    "raw_unit": "N",
                    "final_confidence": 96,
                    "risk_class": "CRITICAL_NUMERIC",
                    "decision_state": "REVIEW_REQUIRED",
                    "quote": "KITO CB010 hand chain pull: 284 N.",
                }
            ]
        )
        captured = {}

        def fake_request(method, path, api_key, body=None, **kwargs):
            captured.update({"method": method, "path": path, "body": body})
            return {"id": "page-1"}

        mapping_path = ROOT / "tests" / "notion-map-test.jsonl"
        try:
            with patch("kf_pilot.notion_sync.validate_data_source_schema"), patch(
                "kf_pilot.notion_sync.find_page_by_candidate_id",
                return_value={"id": "page-1"},
            ), patch("kf_pilot.notion_sync._request", side_effect=fake_request):
                sync_candidates(candidates, "key", "source", "Category", "run-1", mapping_path)
            properties = captured["body"]["properties"]
            self.assertNotIn("Decision", properties)
            self.assertNotIn("Reviewer Note", properties)
        finally:
            mapping_path.unlink(missing_ok=True)

    def test_v2_knowledge_sync_sets_relation_and_never_auto_approves(self):
        candidates = pd.DataFrame([{
            "candidate_id": "knowledge-1", "resource_id": "source-1", "jurisdiction": "VN",
            "claim_family": "SAFETY_GUIDANCE", "predicate": "people_lifting_prohibition",
            "claim_text": "Không được nâng người.", "subject_product_family": "manual hand chain hoist",
            "applicability_scope": "MANUAL_CHAIN_HOIST", "applicability_directness": "DIRECT",
            "authority_tier": "PRIMARY_LEGAL", "legal_status": "CURRENT", "final_confidence": 97,
            "original_url": "https://example.gov/rule",
        }])
        captured = {}
        def fake_request(method, path, api_key, body=None, **kwargs):
            captured.update({"method": method, "path": path, "body": body})
            return {"id": "page-knowledge-1"}
        with patch("kf_pilot.notion_sync.validate_v2_data_source_schema"), patch(
            "kf_pilot.notion_sync.find_page_by_text_id", return_value=None
        ), patch("kf_pilot.notion_sync._request", side_effect=fake_request):
            sync_knowledge_items(candidates, "key", "knowledge-source", {"source-1": "evidence-page-1"}, "run-1")
        props = captured["body"]["properties"]
        self.assertEqual(props["Status"]["select"]["name"], "REVIEW_REQUIRED")
        self.assertEqual(props["Decision"]["select"]["name"], "PENDING")
        self.assertEqual(props["Evidence Sources"]["relation"], [{"id": "evidence-page-1"}])


if __name__ == "__main__":
    unittest.main()
