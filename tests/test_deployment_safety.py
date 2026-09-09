import unittest
from unittest.mock import patch

import pandas as pd

from kf_pilot.canonicalize import canonicalize_knowledge
from kf_pilot.notion_sync import _upsert_page, sync_knowledge_items


class DeploymentSafetyTests(unittest.TestCase):
    def records(self):
        return pd.DataFrame([
            dict(variant_id=x, canonical_scope_key="same", semantic_text=x,
                 numeric_slots_json="{}", conditions_json="[]", atomicity_score=1,
                 claim_text=x, evidence_ids=[x], resource_id=x, final_confidence=90)
            for x in "ABC"
        ])

    def test_complete_link_blocks_transitive_merge(self):
        def relation(a, b):
            pair = frozenset((a["variant_id"], b["variant_id"]))
            return ("SUPPORTING" if pair == frozenset("AC") else "EQUIVALENT", .9)
        with patch("kf_pilot.canonicalize.normalize_claims", return_value=self.records()), patch("kf_pilot.canonicalize._relation", side_effect=relation):
            _, clusters, _, _ = canonicalize_knowledge(pd.DataFrame())
        self.assertEqual(len(clusters), 2)

    def test_supporting_does_not_merge(self):
        with patch("kf_pilot.canonicalize.normalize_claims", return_value=self.records()), patch("kf_pilot.canonicalize._relation", return_value=("SUPPORTING", .8)):
            _, clusters, _, _ = canonicalize_knowledge(pd.DataFrame())
        self.assertEqual(len(clusters), 3)

    def test_hold_overrides_status_not_reviewer_notes(self):
        properties = {"Status": {"select": {"name": "HOLD"}}, "Decision": {"select": {"name": "HOLD"}}, "Reviewer Note": {"rich_text": []}}
        with patch("kf_pilot.notion_sync.find_page_by_text_id", return_value={"id": "p"}), patch("kf_pilot.notion_sync._request", return_value={"id": "p"}) as request:
            _upsert_page("test", "ds", "Knowledge ID", "k", properties, True)
        updated = request.call_args.args[3]["properties"]
        self.assertEqual(updated["Status"]["select"]["name"], "HOLD")
        self.assertNotIn("Decision", updated)
        self.assertNotIn("Reviewer Note", updated)

    def test_new_held_knowledge_is_not_pending(self):
        frame = pd.DataFrame([dict(candidate_id="k", resource_id="s", decision_state="HOLD", claim_text="Held text")])
        with patch("kf_pilot.notion_sync.validate_v2_data_source_schema"), patch("kf_pilot.notion_sync._upsert_page", return_value=({"id": "p"}, "CREATED")) as upsert:
            sync_knowledge_items(frame, "test", "ds", {"s": "source"}, "run")
        self.assertEqual(upsert.call_args.args[4]["Decision"]["select"]["name"], "HOLD")


if __name__ == "__main__":
    unittest.main()
