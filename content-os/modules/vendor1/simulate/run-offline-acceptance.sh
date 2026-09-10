#!/bin/sh
# Re-run contractor acceptance with zero THBISON resources.
set -eu
cd "$(dirname "$0")/.."
export THBISON_MODE=MOCK
unset OPENSEO_API_KEY || true
echo "== unit =="
node --experimental-strip-types --test src/planning/jobs.test.ts
echo "== kit integrity (owner kit, unmodified) =="
python3 vendor_kit/tools/verify_kit.py
echo "== http matrix (requires local MOCK server already serving contract routes) =="
if curl -sf -o /dev/null --max-time 2 http://127.0.0.1:8080/healthz; then
  python3 vendor_tests/test_http_matrix.py
  python3 vendor_tests/consumer_v2.py delivery/sample-brief.json
else
  echo "SKIP http matrix: MOCK server not listening (start npm run dev first)"
fi
echo "== done; see delivery/RECEIPT.json =="
