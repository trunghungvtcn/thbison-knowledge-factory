import tempfile
import unittest
from pathlib import Path

from kf_pilot.v164_semantics.canonical import GateError, sha256
from kf_pilot.v164_semantics.evidence import SourceStore, utf8_units


class LiteralBoundaryTests(unittest.TestCase):
    def check_token(self, text, start, end, numeric):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            raw = text.encode("utf-8")
            (root / "test.txt").write_bytes(raw)
            manifest = [{"source_ref": "test", "path": "test.txt", "raw_sha256": sha256(raw), "extractor_id": "utf8/v1"}]
            store = SourceStore(root, manifest, {"utf8/v1": utf8_units})
            span = {"source_ref": "test", "raw_sha256": sha256(raw), "extractor_id": "utf8/v1",
                    "unit_id": "text:0", "start": start, "end": end, "quote": text[start:end]}
            store.complete_token(span, numeric=numeric)

    def test_one_cannot_be_taken_from_thirty_one(self):
        with self.assertRaises(GateError) as caught:
            self.check_token("31 years", 1, 2, True)
        self.assertEqual(caught.exception.code, "CLIPPED_LITERAL")

    def test_unit_prefix_cannot_be_clipped(self):
        with self.assertRaises(GateError) as caught:
            self.check_token("1 years", 2, 6, False)
        self.assertEqual(caught.exception.code, "CLIPPED_LITERAL")

    def test_complete_decimal_and_unit_are_accepted(self):
        self.check_token("1.5 years", 0, 3, True)
        self.check_token("1.5 years", 4, 9, False)

