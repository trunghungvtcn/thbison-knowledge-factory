"""One-command source/provenance verification for THBISON-INTEGRATION-01."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import subprocess
import sys
from pathlib import Path

from jsonschema import Draft202012Validator, FormatChecker

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
PINS = {
    "core": "3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b",
    "j1": "6fae4c406d7f9a6c00515b19b36db0dcfa16e6a2",
    "j2": "8b197d67f70f6db614a8aefdda7b84f0d4009827",
    "bridge": "601822789da365bd527f0eb0d8b427e713edbc99",
    "contractor": "afac091e60bb6c8a0f0630964e43f5e80951267c",
}


def run(args, *, cwd=ROOT, env=None):
    print("+", " ".join(map(str, args)))
    subprocess.run(args, cwd=cwd, env=env, check=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--full", action="store_true", help="run Linux-only bridge and contractor suites")
    opts = parser.parse_args()
    contractor = ROOT / "dependencies/pipeline-lab-contractor-m1-m5"
    actual = subprocess.run(["git", "rev-parse", "HEAD"], cwd=contractor, check=True, capture_output=True, text=True).stdout.strip()
    if actual != PINS["contractor"]:
        raise SystemExit(f"CONTRACTOR_PIN_MISMATCH:{actual}")
    for sha in (PINS["core"], PINS["j1"], PINS["j2"], PINS["bridge"]):
        run(["git", "cat-file", "-e", f"{sha}^{{commit}}"])
    run([sys.executable, "scripts/jobs/j2_verify_payload.py"])

    env = {**os.environ, "PYTHONPATH": str(ROOT / "src"), "CONTRACTOR_ROOT": str(contractor), "PYTEST_DISABLE_PLUGIN_AUTOLOAD": "1"}
    run([sys.executable, "-m", "pytest", "-q", "tests/jobs/test_content_os_gateway.py"], env=env)
    from kf_pilot.content_os_gateway import map_knowledge_output

    fixture = json.loads((ROOT / "fixtures/integration/knowledge-output.test-only.json").read_text(encoding="utf-8"))
    bundle = map_knowledge_output(fixture, expected_project_id="test-thbison")
    schema = json.loads((ROOT / "content-os/contracts/schemas/EvidenceBundle.json").read_text(encoding="utf-8"))
    errors = list(Draft202012Validator(schema, format_checker=FormatChecker()).iter_errors(bundle))
    if errors:
        raise SystemExit("EVIDENCE_SCHEMA_INVALID:" + ";".join(e.message for e in errors))

    if opts.full:
        run([sys.executable, "-m", "pytest", "-q", "tests/jobs"], env=env)
        run([sys.executable, "run_all.py"], cwd=contractor, env={**env, "PYTHONPATH": ""})
    elif os.name == "nt":
        print("NOT_RUN Linux-only J3 locator/contractor suites; use --full in GitHub Actions")
    print("CANDIDATE_SOURCE_VERIFY_PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
