import unittest
from kf_pilot.v16.condition_ast import canonicalize_ast, migrate_legacy_tags, contains_unresolved
from kf_pilot.v16.decisions import DecisionBinding, effective_decision, build_notion_update
from kf_pilot.v16.migration import LegacyCanonicalRow, migrate_row
from kf_pilot.v16.notion_payload import build_update_only_plan


class V16Tests(unittest.TestCase):
    def row(self, **kw):
        return LegacyCanonicalRow(**dict(dict(legacy_canonical_id="legacy-a", canonical_text="claim",
            predicate="inspection", object_value="annual", notion_page_id="page-a"), **kw))

    def test_order_and_connective(self):
        a = {"op": "COMPARE", "field": "age", "comparator": "GT", "value": 12}
        b = {"op": "COMPARE", "field": "mode", "comparator": "EQ", "value": "mobile"}
        self.assertEqual(canonicalize_ast({"op":"AND","args":[a,b,a]}), canonicalize_ast({"op":"AND","args":[b,a]}))
        self.assertNotEqual(canonicalize_ast({"op":"AND","args":[a,b]}), canonicalize_ast({"op":"OR","args":[a,b]}))

    def test_raw_unknown(self):
        self.assertTrue(contains_unresolved(migrate_legacy_tags([], "except under special circumstances")))
        self.assertTrue(contains_unresolved(migrate_legacy_tags(["A", "B"])))

    def test_no_extra_ast_fields(self):
        with self.assertRaises(ValueError):
            canonicalize_ast({"op":"NOT", "arg":{"op":"TRUE"}, "exception":"lost"})

    def test_identity_and_version(self):
        a = migrate_row(self.row(), "a")
        b = migrate_row(self.row(parsed_condition_ast={"op":"FALSE"}), "b")
        self.assertEqual(a.entity["claim_entity_id"], b.entity["claim_entity_id"])
        self.assertNotEqual(a.version["claim_version_id"], b.version["claim_version_id"])
        self.assertEqual(a.publication_mapping, b.publication_mapping)
        c = migrate_row(self.row(notes="human note"), "c")
        self.assertEqual(a.version["claim_version_id"], c.version["claim_version_id"])

    def test_stale_and_bound(self):
        a = migrate_row(self.row(decision="APPROVED"), "a")
        self.assertEqual(a.decision_binding["effective_decision"], "STALE_REVIEW")
        b = migrate_row(self.row(decision="APPROVED", reviewed_claim_version_id=a.version["claim_version_id"]), "b")
        self.assertEqual(b.decision_binding["effective_decision"], "APPROVED")

    def test_hold_and_unresolved_block(self):
        for status, unresolved in [("HOLD",False),("REJECTED",False),("REVIEW_REQUIRED",True)]:
            self.assertNotEqual(effective_decision(system_status=status,current_claim_version_id="v",
                binding=DecisionBinding("APPROVED","v"),condition_unresolved=unresolved), "APPROVED")

    def test_property_allowlist(self):
        for key in ["Decision", "Review Notes", "Reviewer Note", "unknown"]:
            with self.assertRaises(ValueError): build_notion_update({key:"x"})

    def test_hold_plan_and_duplicate_mapping(self):
        a = migrate_row(self.row(system_status="HOLD"), "a")
        plan = build_update_only_plan([a.version],[a.publication_mapping],run_id="a")
        self.assertEqual(plan["operations"][0]["typed_properties"]["System Status"]["select"]["name"], "HOLD")
        self.assertEqual(plan["created_count"], 0)
        with self.assertRaises(ValueError):
            build_update_only_plan([a.version],[a.publication_mapping,a.publication_mapping],run_id="a")
