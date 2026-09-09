from __future__ import annotations

import argparse
import json
from pathlib import Path

from .artifacts import output_bytes, replay_gate, verify_artifacts, write_artifacts
from .canonical import canonical_bytes, load_json, require, sha256
from .demo import fixture_assets, fixture_pins, fixture_runtime
from .evidence import utf8_units
from .pipeline import run


def main() -> None:
    parser = argparse.ArgumentParser(description="V16.4 TEST_ONLY demo and offline artifact checks")
    commands = parser.add_subparsers(dest="command", required=True)
    demo = commands.add_parser("demo")
    demo.add_argument("--output", type=Path, required=True)
    verify = commands.add_parser("verify")
    verify.add_argument("path", type=Path)
    replay = commands.add_parser("replay")
    replay.add_argument("first", type=Path)
    replay.add_argument("second", type=Path)
    audit = commands.add_parser("audit-demo")
    audit.add_argument("path", type=Path)
    args = parser.parse_args()
    if args.command == "verify":
        print(json.dumps(verify_artifacts(args.path), sort_keys=True))
        return
    if args.command == "replay":
        print(json.dumps(replay_gate(args.first, args.second), sort_keys=True))
        return
    if args.command == "audit-demo":
        source = args.path / "synthetic_inputs"
        saved = args.path / "artifacts"
        verify_artifacts(saved)
        assets = load_json(source / "inputs.json")
        pins = load_json(source / "TEST_ONLY_pins.json")
        recomputed = run(assets, pins, root=source, runtime=fixture_runtime(), extractors={"utf8/v1": utf8_units})
        for name, value in recomputed.items():
            require((saved / name).read_bytes() == output_bytes(name, value), "RECOMPUTATION_MISMATCH", name)
        actual_code = {p.name: sha256(p.read_bytes()) for p in sorted(Path(__file__).parent.glob("*.py"))}
        require(load_json(saved / "v164_code_manifest.json") == actual_code, "CODE_MANIFEST_MISMATCH")
        print("V164_TEST_ONLY_REEXTRACTION_AND_RECOMPUTATION_PASS")
        return
    require(not args.output.exists(), "OUTPUT_ALREADY_EXISTS")
    args.output.mkdir(parents=True)
    source_root = args.output / "synthetic_inputs"
    assets = fixture_assets(source_root)
    pins = fixture_pins(assets)
    (source_root / "inputs.json").write_bytes(canonical_bytes(assets) + b"\n")
    (source_root / "TEST_ONLY_pins.json").write_bytes(canonical_bytes(pins) + b"\n")
    module_root = Path(__file__).parent
    code = {p.name: sha256(p.read_bytes()) for p in sorted(module_root.glob("*.py"))}
    outputs = run(assets, pins, root=source_root, runtime=fixture_runtime(), extractors={"utf8/v1": utf8_units})
    write_artifacts(args.output / "artifacts", outputs, code)
    print(json.dumps(outputs["v164_readiness_report.json"], indent=2, ensure_ascii=False, sort_keys=True))


if __name__ == "__main__":
    main()


