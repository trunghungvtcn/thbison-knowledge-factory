#!/usr/bin/env bash
# Fail closed: every mandatory gate must pass or this script exits nonzero
# and does not write VERIFY_LOCAL_OK.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
LOGDIR="${VERIFY_LOGDIR:-$ROOT/evidence}"
mkdir -p "$LOGDIR"
TS="$(date -u +%Y-%m-%dT%H:%M:%SZ)"
ENVDIR="$(mktemp -d /tmp/v5-clean-XXXX)"
WHEELS="$ROOT/vendor/wheelhouse"
INJECT="${VERIFY_INJECT_FAIL:-}"
SUPPORTED_PY="3.10 3.11 3.12"

fail() {
  local code="$1"; shift
  echo "VERIFY_LOCAL_FAIL: $*" | tee -a "$LOGDIR/verify_local.fail"
  rm -f "$LOGDIR/verify_local.receipt"
  exit "$code"
}

loghdr() {
  local out="$1"
  local cmd="$2"
  {
    echo "command: $cmd"
    echo "cwd: $PWD"
    echo "time: $(date -u +%Y-%m-%dT%H:%M:%SZ)"
    echo "python: $(python3 -V 2>&1)"
  } >"$out"
}

run_gate() {
  local name="$1"
  local logfile="$2"
  shift 2
  set +e
  "$@" >>"$logfile" 2>&1
  local rc=$?
  set -e
  echo "exit_code: $rc" >>"$logfile"
  if [ "$rc" -ne 0 ]; then
    fail "$rc" "gate $name failed with exit $rc (see $logfile)"
  fi
}

cd "$ROOT"

PYVER="$(python3 -c 'import sys; print("%d.%d"%sys.version_info[:2])')"
echo "detected_python: $PYVER" | tee "$LOGDIR/runtime.log"
case " $SUPPORTED_PY " in
  *" $PYVER "*) ;;
  *)
    echo "BLOCKED_ENVIRONMENT: CPython $PYVER not in supported set {$SUPPORTED_PY}" | tee -a "$LOGDIR/runtime.log"
    fail 2 "unsupported Python $PYVER"
    ;;
esac

if [ ! -d "$WHEELS" ]; then
  echo "BLOCKED_ENVIRONMENT: vendor/wheelhouse missing" | tee "$LOGDIR/clean_install.log"
  fail 2 "wheelhouse missing"
fi

loghdr "$LOGDIR/clean_install.log" "python3 -m venv + pip --no-index --find-links wheelhouse"
run_gate venv "$LOGDIR/clean_install.log" python3 -m venv "$ENVDIR/venv"
if [ ! -x "$ENVDIR/venv/bin/python" ]; then
  fail 2 "venv python missing after create"
fi
# shellcheck disable=SC1091
source "$ENVDIR/venv/bin/activate"
if [ -z "${VIRTUAL_ENV:-}" ]; then
  fail 2 "venv activate did not set VIRTUAL_ENV"
fi
run_gate pip_install "$LOGDIR/clean_install.log" pip install --no-index --find-links "$WHEELS" -r "$ROOT/requirements.txt"

if [ "$INJECT" = "pip_check" ]; then
  echo "injected broken extra" > "$ENVDIR/venv/lib/injected_break"
  run_gate pip_check "$LOGDIR/pip_check.log" python -c "import sys; print('injected pip-check fail'); sys.exit(1)"
else
  loghdr "$LOGDIR/pip_check.log" "pip check"
  run_gate pip_check "$LOGDIR/pip_check.log" pip check
fi

export PYTHONPATH="$ROOT"
loghdr "$LOGDIR/unit.log" "pytest tests"
run_gate unit "$LOGDIR/unit.log" python -m pytest tests/test_cms_cases.py tests/test_http.py tests/test_r2_policy.py -q --junitxml="$LOGDIR/junit.xml"

loghdr "$LOGDIR/build.log" "import app.httpapi"
run_gate build "$LOGDIR/build.log" python -c "from app.httpapi import Handler; print('build-ok')"

export CMS_LEDGER_PATH="$ENVDIR/ledger.sqlite"
export STAGING_WRITE_ENABLED=true
loghdr "$LOGDIR/restart.log" "two OS processes process_worker.py"

if [ "$INJECT" = "worker" ]; then
  run_gate worker "$LOGDIR/restart.log" python -c "raise SystemExit(7)"
fi

run_gate worker_p1 "$LOGDIR/restart.log" python "$ROOT/scripts/process_worker.py"
# capture stdout separately
python "$ROOT/scripts/process_worker.py" >"$ENVDIR/p1.json"
echo "p1_exit: 0" >>"$LOGDIR/restart.log"
if [ "$INJECT" = "restart_assert" ]; then
  echo '{"publication_id":"wrong","actual_side_effects":9}' > "$ENVDIR/p2.json"
else
  python "$ROOT/scripts/process_worker.py" >"$ENVDIR/p2.json"
fi
echo "p2_written" >>"$LOGDIR/restart.log"
cat "$ENVDIR/p1.json" "$ENVDIR/p2.json" >>"$LOGDIR/restart.log"

run_gate restart_assert "$LOGDIR/restart.log" python - <<PY
import json, os, subprocess, sys
from pathlib import Path
p1=json.loads(Path("$ENVDIR/p1.json").read_text())
p2=json.loads(Path("$ENVDIR/p2.json").read_text())
assert p1["publication_id"]==p2["publication_id"], (p1, p2)
assert p1["provider_record_id"]==p2["provider_record_id"]
env=os.environ.copy()
env["PYTHONPATH"]="$ROOT"
env["CMS_LEDGER_PATH"]="$ENVDIR/ledger.sqlite"
r=subprocess.run([sys.executable, "$ROOT/scripts/process_worker.py", "stats"], env=env, capture_output=True, text=True, check=True)
stats=json.loads(r.stdout)
assert stats["side_effects"]==1, stats
print("OS_PROCESS_RESTART_OK")
PY

if [ -n "$INJECT" ]; then
  fail 1 "inject $INJECT should have failed earlier"
fi

echo "VERIFY_LOCAL_OK $TS" | tee "$LOGDIR/verify_local.receipt"
