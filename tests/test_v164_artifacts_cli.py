from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from kf_pilot.v164_semantics.artifacts import replay_gate, verify_artifacts
from kf_pilot.v164_semantics.canonical import GateError, canonical_bytes, load_json, sha256

ROOT = Path(__file__).resolve().parents[1]


class ArtifactTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.env = dict(os.environ, PYTHONPATH=str(ROOT / "src"))

    def tearDown(self):
        self.temp.cleanup()

    def cli(self, *args):
        return subprocess.run([sys.executable, "-m", "kf_pilot.v164_semantics", *map(str, args)],
                              env=self.env, cwd=ROOT, capture_output=True, text=True, check=False)

    def test_cli_demo_audit_reextracts_and_recomputes(self):
        result = self.cli("demo", "--output", self.root / "first")
        self.assertEqual(result.returncode, 0, result.stderr)
        result = self.cli("audit-demo", self.root / "first")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("RECOMPUTATION_PASS", result.stdout)

    def test_identical_runs_are_byte_equal(self):
        for name in ("first", "second"):
            self.assertEqual(self.cli("demo", "--output", self.root / name).returncode, 0)
        result = replay_gate(self.root / "first/artifacts", self.root / "second/artifacts")
        self.assertEqual(result["status"], "BYTE_AND_HASH_EQUALITY_PASS")

    def test_output_directory_must_be_new(self):
        self.cli("demo", "--output", self.root / "first")
        result = self.cli("demo", "--output", self.root / "first")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("OUTPUT_ALREADY_EXISTS", result.stderr)

    def test_rehashed_forged_totals_fail_recomputation(self):
        self.cli("demo", "--output", self.root / "first")
        path = self.root / "first/artifacts"
        report = load_json(path / "v164_readiness_report.json")
        report["accepted_derivations"] = 999
        data = canonical_bytes(report) + b"\n"
        (path / "v164_readiness_report.json").write_bytes(data)
        manifest = load_json(path / "artifact_hashes.json")
        manifest["v164_readiness_report.json"] = sha256(data)
        (path / "artifact_hashes.json").write_bytes(canonical_bytes(manifest) + b"\n")
        # Self-consistent hashes do not prove execution; recomputation catches this.
        verify_artifacts(path)
        result = self.cli("audit-demo", self.root / "first")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("RECOMPUTATION_MISMATCH", result.stderr)

    def test_missing_artifact_fails(self):
        self.cli("demo", "--output", self.root / "first")
        path = self.root / "first/artifacts"
        (path / "v164_adapter_inputs.jsonl").unlink()
        with self.assertRaises(GateError):
            verify_artifacts(path)

    def test_cli_has_no_production_flag(self):
        result = self.cli("--write-production")
        self.assertNotEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()

