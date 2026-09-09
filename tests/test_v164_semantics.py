from __future__ import annotations

import copy
import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from kf_pilot.v164_semantics.canonical import GateError, digest
from kf_pilot.v164_semantics.demo import fixture_assets, fixture_pins, fixture_runtime, fixture_upstream_hash
from kf_pilot.v164_semantics.evidence import utf8_units
from kf_pilot.v164_semantics.integration import repository_runtime
from kf_pilot.v164_semantics.pipeline import run
from kf_pilot.v164_semantics.review import REQUIRED_CHECKS


class SemanticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.assets = fixture_assets(self.root)

    def tearDown(self):
        self.temp.cleanup()

    def execute(self, assets=None, pins=None):
        current = assets if assets is not None else self.assets
        return run(current, pins if pins is not None else fixture_pins(current), root=self.root,
                   runtime=fixture_runtime(), extractors={"utf8/v1": utf8_units})

    def candidate(self, index=0):
        return self.assets["snapshot"]["candidates"][index]

    def reseal(self, candidate=None):
        value = candidate if candidate is not None else self.candidate()
        value["upstream_binding_hash"] = fixture_upstream_hash(value)

    def reviewer(self):
        self.assets["reviewer_registry"]["entries"]["fixture-reviewer"] = {
            "data_class": "TEST_ONLY", "active": True, "roles": ["SEMANTIC_REVIEWER"],
            "predicates": ["DEMO_INTERVAL", "DEMO_PROHIBITION"],
            "valid_from": "2026-01-01T00:00:00Z", "valid_until": "2027-01-01T00:00:00Z"}

    def review(self, decision="ACCEPT", proposal=None):
        self.reviewer()
        proposal = proposal or self.execute()["v164_semantic_proposals.jsonl"][0]
        value = {key: proposal[key] for key in
                 ("proposal_hash", "issue_id", "entity_id", "base_version_id", "target_version_id")}
        value.update(decision=decision, reviewer_id="fixture-reviewer", decided_at="2026-09-04T00:00:00Z",
                     rationale="TEST ONLY: synthetic adjudication exercises validation, never real approval.",
                     checks={key: True for key in sorted(REQUIRED_CHECKS)}, data_class="TEST_ONLY")
        self.assets["adjudications"]["entries"].append(value)
        return value

    def code(self, expected, action):
        with self.assertRaises(GateError) as caught:
            action()
        self.assertEqual(caught.exception.code, expected)

    def diagnostic(self):
        return self.execute()["v164_candidate_diagnostics.jsonl"][0]

    def test_zero_accept_keeps_every_issue_unresolved(self):
        result = self.execute()
        report = result["v164_readiness_report.json"]
        self.assertEqual(report["issues"], 6)
        self.assertEqual(report["valid_proposals"], 2)
        self.assertEqual(report["blocked_candidates"], 3)
        self.assertEqual(report["accepted_derivations"], 0)
        self.assertEqual(report["upstream_unresolved"], 6)
        self.assertEqual({r["issue_id"] for r in result["v164_issue_accounting.jsonl"]},
                         {r["issue_id"] for r in self.assets["snapshot"]["issues"]})

    def test_valid_human_accept_still_hits_whole_literal_restriction(self):
        self.review()
        result = self.execute()
        self.assertEqual(len(result["v164_accepted_derivations.jsonl"]), 1)
        self.assertEqual(result["v164_review_results.jsonl"][0]["adapter_status"], "V162_CONTRACT_INCOMPATIBLE")
        self.assertEqual(result["v164_adapter_inputs.jsonl"], [])
        self.assertEqual(result["v164_readiness_report.json"]["resolved_by_this_run"], 0)

    def test_compatible_test_literal_produces_input_but_never_claims_resolution(self):
        self.assets["snapshot"]["issues"][0]["source_text"] = "1 year"
        self.review()
        result = self.execute()
        self.assertEqual(len(result["v164_adapter_inputs.jsonl"]), 1)
        self.assertEqual(result["v164_readiness_report.json"]["resolved_by_this_run"], 0)
        self.assertEqual(result["v164_phase_f_canary_plan.json"]["records"], [])

    def test_changed_baseline_fails(self):
        (self.root / "baseline.json").write_text("changed", encoding="utf-8")
        self.code("V161_BASELINE_MISMATCH", self.execute)

    def test_changed_source_fails(self):
        (self.root / "synthetic-source.txt").write_text("changed", encoding="utf-8")
        self.code("SOURCE_HASH_MISMATCH", self.execute)

    def test_registry_tampering_fails_against_independent_pin(self):
        pins = fixture_pins(self.assets)
        self.reviewer()
        self.code("INPUT_PIN_MISMATCH", lambda: self.execute(pins=pins))

    def test_quote_tampering_blocks_candidate(self):
        self.candidate()["proofs"]["amount"]["quote"] = "9"
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "EXACT_QUOTE_MISMATCH")

    def test_wrong_offset_blocks_candidate(self):
        self.candidate()["proofs"]["amount"]["start"] += 1
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "LOCATOR_OFFSETS_INVALID")

    def test_wrong_page_blocks_candidate(self):
        self.candidate()["context_span"]["unit_id"] = "pdf_page:67"
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "LOCATOR_UNIT_MISMATCH")

    def test_wrong_extract_method_blocks_candidate(self):
        self.candidate()["context_span"]["extractor_id"] = "other"
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "EXTRACTOR_ID_MISMATCH")

    def test_amount_cannot_be_invented(self):
        self.candidate()["interpretation"]["amount"] = "999"
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "AMOUNT_NOT_PROVEN")

    def test_unknown_unit_blocks(self):
        self.candidate()["interpretation"]["unit"] = "ambiguous-ton"
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "UNIT_NOT_IN_CONTRACT")

    def test_boolean_is_not_a_numeric_value(self):
        self.candidate()["interpretation"]["amount"] = True
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "EXPLICIT_DECIMAL_REQUIRED")

    def test_uncontracted_operator_blocks(self):
        self.candidate()["interpretation"]["operator"] = "LTE"
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "OPERATOR_NOT_IN_CONTRACT")

    def test_scope_drift_blocks(self):
        self.candidate()["applicability"] = {"scope": "ALL_PRODUCTS_WORLDWIDE"}
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "APPLICABILITY_MISMATCH")

    def test_predicate_drift_blocks(self):
        self.candidate()["predicate"] = "RATED_LOAD"
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "PREDICATE_MISMATCH")

    def test_foreign_entity_blocks(self):
        self.candidate()["entity_id"] = "demo-entity-1"
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "CANDIDATE_ENTITY_MISMATCH")

    def test_candidate_version_drift_blocks(self):
        self.candidate()["base_version_id"] = "another"
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "CANDIDATE_VERSION_MISMATCH")

    def test_unknown_semantic_field_blocks(self):
        self.candidate()["interpretation"]["guess"] = True
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "UNKNOWN_FIELDS")

    def test_full_context_cannot_be_replaced_by_number_only(self):
        self.candidate()["context_span"] = copy.deepcopy(self.candidate()["proofs"]["amount"])
        self.reseal()
        self.assertEqual(self.diagnostic()["reason"], "FULL_LEGACY_CONTEXT_MISSING")

    def test_unpinned_enum_vocabulary_blocks(self):
        result = self.execute()
        self.assertTrue(all(row["reason"] == "AUTHORITATIVE_VOCABULARY_MISSING"
                            for row in result["v164_candidate_diagnostics.jsonl"][2:]))

    def test_pinned_test_vocabulary_allows_proposals_only(self):
        entries = {f"PROHIBITION_{i}": {"definition": f"TEST ONLY definition {i}",
                    "source_literals": [self.candidate(i)["proofs"]["statement"]["quote"]]} for i in range(2, 5)}
        self.assets["vocabularies"]["entries"] = {"demo-vocab": {
            "authority_ref": "TEST_ONLY_AUTHORITY", "version": "test-v1", "entries": entries}}
        report = self.execute()["v164_readiness_report.json"]
        self.assertEqual(report["valid_proposals"], 5)
        self.assertEqual(report["accepted_derivations"], 0)

    def test_unbound_or_stale_review_rejected(self):
        review = self.review()
        review["target_version_id"] = "stale-version"
        self.code("ADJUDICATION_BINDING_MISMATCH", self.execute)

    def test_untrusted_reviewer_rejected(self):
        self.review()["reviewer_id"] = "invented-user"
        self.code("REVIEWER_NOT_TRUSTED", self.execute)

    def test_self_adjudication_rejected(self):
        review = self.review()
        registry = self.assets["reviewer_registry"]["entries"]
        registry["DEMO_MODEL"] = registry["fixture-reviewer"]
        review["reviewer_id"] = "DEMO_MODEL"
        self.code("SELF_ADJUDICATION_REJECTED", self.execute)

    def test_inactive_reviewer_rejected(self):
        self.review()
        self.assets["reviewer_registry"]["entries"]["fixture-reviewer"]["active"] = False
        self.code("REVIEWER_INACTIVE", self.execute)

    def test_reviewer_scope_rejected(self):
        self.review()
        self.assets["reviewer_registry"]["entries"]["fixture-reviewer"]["predicates"] = []
        self.code("REVIEWER_SCOPE_MISMATCH", self.execute)

    def test_fake_truthy_checks_rejected(self):
        review = self.review()
        review["checks"]["no_omitted_requirements"] = "true"
        self.code("INCOMPLETE_SEMANTIC_REVIEW", self.execute)

    def test_future_review_rejected(self):
        self.review()["decided_at"] = "2030-01-01T00:00:00Z"
        self.code("REVIEW_FROM_FUTURE", self.execute)

    def test_duplicate_adjudications_rejected(self):
        review = self.review()
        self.assets["adjudications"]["entries"].append(copy.deepcopy(review))
        self.code("DUPLICATE_ID", self.execute)

    def test_rejected_review_produces_no_adapter_input(self):
        self.review("REJECT")
        result = self.execute()
        self.assertEqual(result["v164_adapter_inputs.jsonl"], [])
        self.assertEqual(result["v164_accepted_derivations.jsonl"], [])

    def test_needs_evidence_decision_produces_no_adapter_input(self):
        self.review("NEEDS_MORE_EVIDENCE")
        self.assertEqual(self.execute()["v164_adapter_inputs.jsonl"], [])

    def test_human_hold_wins_over_accepted_binding(self):
        self.assets["snapshot"]["records"][0]["decision"] = "HOLD"
        self.review()
        result = self.execute()
        self.assertEqual(result["v164_review_results.jsonl"][0]["adapter_status"], "BLOCKED_EXISTING_HOLD_OR_REJECTION")
        self.assertEqual(result["v164_adapter_inputs.jsonl"], [])

    def test_approved_record_is_not_binding_accept(self):
        self.assets["snapshot"]["records"][0]["decision"] = "APPROVED"
        self.assertEqual(self.execute()["v164_accepted_derivations.jsonl"], [])

    def test_mapping_collision_fails_batch(self):
        self.assets["snapshot"]["records"][1]["page_id"] = "demo-page-0"
        self.code("MAPPING_COLLISION", self.execute)

    def test_missing_mapping_fails_batch(self):
        self.assets["snapshot"]["records"][0]["page_id"] = None
        self.code("RECORD_FIELD_MISSING", self.execute)

    def test_duplicate_issue_identity_fails(self):
        duplicate = copy.deepcopy(self.assets["snapshot"]["issues"][0])
        duplicate["issue_id"] = "different-id-same-issue"
        self.assets["snapshot"]["issues"].append(duplicate)
        self.code("DUPLICATE_ISSUE_IDENTITY", self.execute)

    def test_before_value_hash_drift_fails(self):
        self.assets["snapshot"]["issues"][0]["before_value_hash"] = "0" * 64
        self.code("ISSUE_BEFORE_HASH_MISMATCH", self.execute)

    def test_unknown_candidate_issue_fails(self):
        self.candidate()["issue_id"] = "orphan"
        self.code("ORPHAN_CANDIDATE", self.execute)

    def test_proposal_preserves_full_scope_and_exceptions(self):
        proposal = self.execute()["v164_semantic_proposals.jsonl"][0]
        original = self.assets["snapshot"]["records"][0]["semantic_payload"]
        for key in original:
            if key != "object_value":
                self.assertEqual(proposal["target_semantic_payload"][key], original[key])
        self.assertEqual(proposal["source_text"], self.assets["snapshot"]["issues"][0]["source_text"])

    def test_display_rewording_keeps_semantic_version(self):
        before = self.execute()["v164_semantic_proposals.jsonl"][0]
        self.assets["snapshot"]["records"][0]["canonical_text"] = "Another TEST ONLY presentation"
        after = self.execute()["v164_semantic_proposals.jsonl"][0]
        self.assertEqual(before["target_version_id"], after["target_version_id"])
        self.assertNotEqual(before["proposal_hash"], after["proposal_hash"])

    def test_one_row_change_is_local(self):
        before = self.execute()["v164_semantic_proposals.jsonl"]
        self.assets["snapshot"]["records"][0]["semantic_payload"]["exception_ast"]["value"] = "updated-demo-exception"
        after = self.execute()["v164_semantic_proposals.jsonl"]
        self.assertNotEqual(before[0]["target_version_id"], after[0]["target_version_id"])
        self.assertEqual(before[1], after[1])

    def test_reverse_order_changes_only_input_manifest_pins(self):
        before = self.execute()
        for name in ("records", "issues", "candidates"):
            self.assets["snapshot"][name].reverse()
        after = self.execute()
        for key in before.keys() - {"v164_input_manifest.json"}:
            self.assertEqual(before[key], after[key], key)

    def test_inputs_notes_and_baseline_are_immutable(self):
        before = copy.deepcopy(self.assets)
        baseline = (self.root / "baseline.json").read_bytes()
        result = self.execute()
        self.assertEqual(before, self.assets)
        self.assertEqual(baseline, (self.root / "baseline.json").read_bytes())
        self.assertEqual(result["v164_human_audit_snapshot.jsonl"][0]["reviewer_note"], "Preserve note 0")

    def test_test_registry_cannot_enter_repository_run(self):
        self.assets["snapshot"]["data_class"] = "REPOSITORY"
        self.code("TEST_DATA_CLASS_MISMATCH", self.execute)

    def test_real_repository_adapter_is_not_faked(self):
        self.code("REPOSITORY_ADAPTER_NOT_CONNECTED", repository_runtime)

    def test_all_mutation_counters_are_zero(self):
        report = self.execute()["v164_readiness_report.json"]
        for key in ("production_writes", "human_field_writes", "create_operations", "sql_executions",
                    "schema_mutations", "scheduler_actions", "eligible_production_records", "eligible_canary_records"):
            self.assertEqual(report[key], 0)
        self.assertIs(report["authorized_to_execute"], False)

    def test_core_needs_no_network_or_file_mutations(self):
        with patch("socket.socket", side_effect=AssertionError("Network forbidden")), \
             patch.object(Path, "write_bytes", side_effect=AssertionError("Core writes forbidden")), \
             patch.object(Path, "write_text", side_effect=AssertionError("Core writes forbidden")):
            self.execute()

    def test_multiple_accepts_for_one_entity_fail(self):
        duplicate = copy.deepcopy(self.candidate())
        duplicate["candidate_id"] = "demo-candidate-another"
        self.reseal(duplicate)
        self.assets["snapshot"]["candidates"].append(duplicate)
        proposals = self.execute()["v164_semantic_proposals.jsonl"]
        matching = [p for p in proposals if p["entity_id"] == "demo-entity-0"]
        for proposal in matching:
            self.review(proposal=proposal)
        self.code("MULTIPLE_ACCEPTS_PER_ENTITY", self.execute)

    def test_source_path_traversal_rejected(self):
        self.assets["snapshot"]["sources"][0]["path"] = "../escape.txt"
        self.code("SOURCE_PATH_ESCAPE", self.execute)

    def test_connective_issue_is_never_inferred_from_object_candidate(self):
        candidate = copy.deepcopy(self.candidate())
        issue = self.assets["snapshot"]["issues"][5]
        record = self.assets["snapshot"]["records"][5]
        candidate.update(candidate_id="z-condition", issue_id=issue["issue_id"], entity_id=issue["entity_id"],
                         base_version_id=issue["version_id"], predicate=record["semantic_payload"]["predicate"],
                         applicability=record["semantic_payload"]["applicability"])
        # Even an exact object span cannot prove the condition's connective.
        self.reseal(candidate)
        self.assets["snapshot"]["candidates"].append(candidate)
        result = self.execute()["v164_candidate_diagnostics.jsonl"][-1]
        self.assertEqual(result["status"], "BLOCKED")
        self.assertEqual(result["reason"], "FULL_LEGACY_CONTEXT_MISSING")


if __name__ == "__main__":
    unittest.main()

