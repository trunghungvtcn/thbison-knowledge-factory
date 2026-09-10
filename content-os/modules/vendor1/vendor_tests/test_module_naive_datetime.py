"""Module compensates for kit test_naive_date_rejected (frozen, FAIL)."""
from __future__ import annotations
import json, os, sys, urllib.request, urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor_kit" / "tools"))
from contracts import validate, ContractError  # type: ignore

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8080")
TOKEN = "thbison-test-token-aaaaaaaa"
NAIVE = "2030-01-01T00:00:00"
AWARE = "2030-01-01T00:00:00Z"


def kit_still_accepts_naive() -> bool:
    brief = json.loads((ROOT / "vendor_kit/contracts/examples/ContentBrief.json").read_text())
    brief["proposed_publish_at"] = NAIVE
    try:
        validate("ContentBrief", brief)
        return True
    except ContractError:
        return False


def http(method, path, body, extra=None):
    h = {
        "Authorization": f"Bearer {TOKEN}",
        "X-Contract-Version": "1.0.0",
        "Content-Type": "application/json",
        "Idempotency-Key": "idempotency-key-naive01",
    }
    if extra:
        h.update(extra)
    data = json.dumps(body).encode()
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=20) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode())


def research():
    return {
        "contract_version": "1.0.0",
        "project_id": "test-thbison",
        "data_class": "TEST_ONLY",
        "request_id": "test-request-naive",
        "scope": {"country_code": "VN", "language": "vi", "timezone": "Asia/Bangkok", "domain": "manual-chain-hoist"},
        "seeds": ["pa lăng xích kéo tay"],
        "existing_pages": [],
        "budget": {
            "max_provider_requests": 3,
            "max_tokens": 1000,
            "max_cost_usd": "0.500000",
            "deadline_at": NAIVE,
            "max_transport_attempts": 2,
        },
    }


def main():
    assert kit_still_accepts_naive(), "unexpected: frozen kit now rejects naive (do not patch kit)"
    st, err = http("POST", "/v1/planning/jobs", research())
    msg = (err.get("message") or "").lower()
    assert st == 400 and err.get("code") == "VALIDATION_ERROR", err
    assert "naive" in msg or "timezone-aware" in msg, err
    print("PASS module rejects naive deadline_at; kit validate() still accepts (upstream FAIL documented)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
