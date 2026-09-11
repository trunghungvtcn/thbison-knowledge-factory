"""Independent content/re-extraction/replay gate for V16.4 artifacts."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from run_semantic import ROOT, compute_outputs

from kf_pilot.v164_semantics.artifacts import output_bytes, replay_gate, verify_artifacts
from kf_pilot.v164_semantics.canonical import load_json, require


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("final", type=Path)
    parser.add_argument("replay", type=Path)
    args = parser.parse_args()
    verify_artifacts(args.final)
    verify_artifacts(args.replay)
    replay = replay_gate(args.final, args.replay)
    expected = compute_outputs()
    for name, value in expected.items():
        require((args.final / name).read_bytes() == output_bytes(name, value),
                "INDEPENDENT_RECOMPUTATION_MISMATCH", name)
    report = load_json(args.final / "v164_readiness_report.json")
    canary = load_json(args.final / "v164_phase_f_canary_plan.json")
    require(report["records"] == 70 and report["issues"] == 79 and report["candidates"] == 5,
            "REPOSITORY_COUNTS_MISMATCH")
    require(report["accepted_derivations"] == report["compatible_adapter_inputs"] == 0,
            "UNEXPECTED_ACCEPTANCE")
    for name in ("production_writes", "human_field_writes", "create_operations",
                 "sql_executions", "schema_mutations", "scheduler_actions"):
        require(report[name] == 0, "MUTATION_COUNTER_NONZERO", name)
    require(canary == {"records": [], "authorized_to_execute": False,
                       "reason": "ZERO_ACCEPTED_DERIVATIONS_AND_PHASE_F_NOT_AUTHORIZED"},
            "CANARY_NOT_FAIL_CLOSED")
    print(json.dumps({"status": "V164_INDEPENDENT_GATE_PASS", "replay": replay}, sort_keys=True))


if __name__ == "__main__":
    main()

