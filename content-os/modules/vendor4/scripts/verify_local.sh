#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 --version
python3 -m pip --version
audit_env_dir="$(mktemp -d)"
set +e
python3 -m venv "$audit_env_dir/venv"
venv_rc=$?
set -e
mkdir -p evidence
python3 - <<PY
import json, hashlib, os, sys, time
from pathlib import Path
receipt = {
  "command": "python3 -m venv",
  "cwd": os.getcwd(),
  "start": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "end": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
  "exit_code": int("$venv_rc"),
  "log_sha256": None,
}
Path("evidence/g1_venv.json").write_text(json.dumps(receipt, indent=2)+"\n")
PY
if [[ "$venv_rc" -ne 0 ]]; then
  echo "G1 BLOCKED_ENVIRONMENT: python3 -m venv failed" >&2
  echo "ensurepip/venv missing" > evidence/g1_stderr.txt
  exit 2
fi
"$audit_env_dir/venv/bin/python" -m pip install --no-cache-dir -r requirements.lock
"$audit_env_dir/venv/bin/python" -m pip check
mkdir -p evidence
"$audit_env_dir/venv/bin/python" -m pytest -ra --junitxml=evidence/junit.xml
