#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
python "$ROOT/v162/gate_phase_f_readiness.py" "$ROOT/v162/example_readiness_report.json" "$ROOT/v162/example_empty_canary.json"
echo "V162_PACK_SMOKE_PASS"
