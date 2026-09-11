from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from kf_pilot.runtime_contract import RunContract, execute_test_only  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one bounded TEST_ONLY Knowledge Factory contract")
    parser.add_argument("--contract", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = execute_test_only(RunContract.load(args.contract), ROOT, args.snapshot, args.output)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

