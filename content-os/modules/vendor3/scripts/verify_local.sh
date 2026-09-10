#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
python3 --version
python3 -m pip --version
audit_env_dir="$(mktemp -d)"
python3 -m venv "$audit_env_dir/venv"
"$audit_env_dir/venv/bin/python" -m pip install --no-cache-dir -U pip
"$audit_env_dir/venv/bin/python" -m pip install --no-cache-dir -r requirements.lock
"$audit_env_dir/venv/bin/python" -m pip check
mkdir -p evidence
"$audit_env_dir/venv/bin/python" -m pytest -ra --junitxml=evidence/junit.xml
echo "AUDIT_ENV=$audit_env_dir"
