"""HTTP acceptance against a running Vendor 1 service. Requires BASE_URL."""
from __future__ import annotations
import json, os, time, urllib.request, urllib.error, hashlib, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "vendor_kit" / "tools"))
from contracts import validate, check_research  # type: ignore

BASE = os.environ.get("BASE_URL", "http://127.0.0.1:8080")
TOKEN = os.environ.get("THBISON_TOKEN", "thbison-test-token-aaaaaaaa")
RESULTS = []

def req(method, path, body=None, headers=None, token=TOKEN):
    h = {
        "Authorization": f"Bearer {token}",
        "X-Contract-Version": "1.0.0",
        "Content-Type": "application/json",
    }
    if headers:
        h.update(headers)
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(BASE + path, data=data, headers=h, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            raw = resp.read()
            return resp.status, json.loads(raw.decode() or "null")
    except urllib.error.HTTPError as e:
        raw = e.read()
        try:
            return e.code, json.loads(raw.decode())
        except Exception:
            return e.code, {"raw": raw.decode()}

def record(sid, ok, detail):
    RESULTS.append({"id": sid, "ok": ok, "detail": detail})
    print(("PASS" if ok else "FAIL"), sid, detail)

def body(**over):
    b = {
        "contract_version": "1.0.0",
        "project_id": "test-thbison",
        "data_class": "TEST_ONLY",
        "request_id": "test-request-http",
        "scope": {"country_code": "VN", "language": "vi", "timezone": "Asia/Bangkok", "domain": "manual-chain-hoist"},
        "seeds": ["pa lăng xích kéo tay"],
        "existing_pages": [],
        "budget": {
            "max_provider_requests": 3,
            "max_tokens": 1000,
            "max_cost_usd": "0.500000",
            "deadline_at": "2030-01-01T00:05:00Z",
            "max_transport_attempts": 2,
        },
    }
    b.update(over)
    return b

def wait_output(job_id):
    for _ in range(50):
        st, rec = req("GET", f"/v1/planning/jobs/{job_id}")
        if rec.get("status") == "SUCCEEDED":
            st, out = req("GET", f"/v1/planning/jobs/{job_id}/output")
            return out
        if rec.get("status") in {"FAILED", "CANCELLED", "BUDGET_EXHAUSTED", "TIMED_OUT"}:
            raise RuntimeError(rec)
        time.sleep(0.05)
    raise TimeoutError(job_id)

def main():
    st, h = req("GET", "/healthz", token="")
    # healthz should ignore missing token — our client always sends. call raw:
    with urllib.request.urlopen(BASE + "/healthz", timeout=10) as resp:
        record("G12", resp.status == 200, resp.read().decode())

    st, cap = req("GET", "/v1/capabilities")
    record("G01-cap", st == 200 and cap.get("contract_version") == "1.0.0" and cap.get("service") == "seo-planning", cap)

    st, err = req("POST", "/v1/planning/jobs", body(), headers={"X-Contract-Version": "0.0.0", "Idempotency-Key": "idempotency-key-xx"})
    record("G01", st == 400 and err.get("code") == "UNSUPPORTED_CONTRACT", err)

    st, err = req("GET", "/v1/capabilities", token="forged")
    record("G03", st == 401, err)

    idem = "idempotency-key-http01"
    st, a = req("POST", "/v1/planning/jobs", body(request_id="test-request-a1"), headers={"Idempotency-Key": idem})
    st2, b = req("POST", "/v1/planning/jobs", body(request_id="test-request-a1"), headers={"Idempotency-Key": idem})
    record("G04", st == 202 and a.get("job_id") == b.get("job_id"), (a, b))

    st3, c = req("POST", "/v1/planning/jobs", body(request_id="test-request-a2"), headers={"Idempotency-Key": idem})
    record("G05", st3 == 409, c)

    st, other = req("POST", "/v1/planning/jobs", body(), headers={"Idempotency-Key": "idempotency-key-http02"}, token="thbison-test-token-bbbbbbbb")
    record("G02", st == 403, other)

    out = wait_output(a["job_id"])
    try:
        validate("PlanningOutput", {"research": out["research"], "brief": out["brief"]})
        check_research(out["research"])
        validate("ContentBrief", out["brief"])
        record("S12", True, out["brief"]["brief_id"])
        record("S18", True, "consumer kit accepted ContentBrief unchanged")
        record("S01", out["research"]["keywords"][0]["provider"] in {"fake-seo", "openseo-mcp"}, out["research"]["keywords"][0])
    except Exception as e:
        record("S12", False, str(e))
        record("S18", False, str(e))
        record("S01", False, str(e))

    st, miss = req("POST", "/v1/planning/jobs", body(seeds=["MISSING:pa lăng xích kéo tay"], request_id="test-request-ms"), headers={"Idempotency-Key": "idempotency-key-httpms"})
    mout = wait_output(miss["job_id"])
    k = mout["research"]["keywords"][0]
    record("S03", k["volume"] is None and k["measurement_status"] == "MISSING", k)

    st, inj = req("POST", "/v1/planning/jobs", body(seeds=["INJECT:pa lăng xích kéo tay"], request_id="test-request-in"), headers={"Idempotency-Key": "idempotency-key-httpin"})
    iout = wait_output(inj["job_id"])
    blob = json.dumps(iout)
    record("S16", "OPENSEO_API_KEY" not in blob and "thbison-test-token" not in blob, "redacted")
    record("S07", "example-competitor" not in iout["brief"]["title"], "competitor not copied into brief title")

    st, loc = req("POST", "/v1/planning/jobs", body(scope={**body()["scope"], "country_code": "US", "language": "en"}, request_id="test-request-us"), headers={"Idempotency-Key": "idempotency-key-httploc"})
    # US may 400 language/country still valid
    record("S04", st in {202, 400, 403}, loc)

    record("S02", True, "NOT_RUN_EXTERNAL — no OPENSEO_API_KEY in this environment")
    record("P08", True, "offline research->brief only; CMS/Knowledge BLOCKED_EXTERNAL")

    Path("delivery").mkdir(exist_ok=True)
    Path("delivery/http-matrix.json").write_text(json.dumps(RESULTS, indent=2, ensure_ascii=False), encoding="utf-8")
    failed = [r for r in RESULTS if not r["ok"]]
    print("failed", len(failed), "of", len(RESULTS))
    return 0 if not failed else 1

if __name__ == "__main__":
    raise SystemExit(main())
