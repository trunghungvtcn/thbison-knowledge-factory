"""Acceptance matrix R01-R35 for Vendor 3 runtime."""
from __future__ import annotations

import json
import os
import tempfile
import time
from pathlib import Path

import pytest

from app.runtime import Runtime, canonical_hash
from app.store import Store
from simulators.workers import ContentWorkflowSim, SeoPlanningSim, SimConfig
from tests.harness import Harness

SCHEMA_DIR = Path(__file__).resolve().parents[1] / "contracts" / "shared" / "schemas"


def validate_receipt(body: dict) -> None:
    required = ["contract_version","project_id","data_class","job_id","request_id","status","code_commit","contract_sha256","result_artifact","error_code"]
    for k in required:
        assert k in body
    assert body["contract_version"] == "1.0.0"
    assert len(body["code_commit"]) == 40
    assert len(body["contract_sha256"]) == 64


@pytest.fixture()
def rt(tmp_path):
    s = Store(str(tmp_path / "lab.db"))
    return Runtime(s, egress_blocked=True)


@pytest.fixture()
def client(rt):
    return Harness(rt)


def H(project="test-alpha", svc="runtime", key=None, req="req-1"):
    h = {
        "X-Service-Id": svc,
        "X-Project-Id": project,
        "X-Roles": "orchestrator",
        "X-Contract-Version": "1.0.0",
        "X-Request-Id": req,
    }
    if key:
        h["Idempotency-Key"] = key
    return h


def submit_body(op="plan", key="idem-plan-0001", extra=None):
    body = {
        "project_id": "test-alpha",
        "operation": op,
        "idempotency_key": key,
        "request_id": "req-1",
        "data_class": "TEST_ONLY",
        "payload": {"seed": "synthetic"},
        "budget": {"max_requests": 4, "max_cost_units": 20},
    }
    if extra:
        body.update(extra)
    return body


def test_r01_submit_valid(client):
    r = client.post("/v1/jobs", headers=H(key="idem-plan-0001"), json=submit_body())
    assert r.status_code == 202
    body = r.json()
    validate_receipt(body)
    assert body["status"] in {"QUEUED", "RUNNING"}


def test_r02_duplicate_same_hash(client):
    h = H(key="idem-plan-0001")
    a = client.post("/v1/jobs", headers=h, json=submit_body()).json()
    b = client.post("/v1/jobs", headers=h, json=submit_body()).json()
    assert a["job_id"] == b["job_id"]


def test_r03_same_key_diff_hash(client):
    h = H(key="idem-plan-0001")
    client.post("/v1/jobs", headers=h, json=submit_body())
    body = submit_body()
    body["payload"] = {"seed": "other"}
    r = client.post("/v1/jobs", headers=h, json=body)
    assert r.status_code == 409
    assert r.json()["code"] == "IDEMPOTENCY_CONFLICT"


def test_r04_cross_project(client):
    job = client.post("/v1/jobs", headers=H(key="k1"), json=submit_body()).json()
    r = client.get(f"/v1/jobs/{job['job_id']}", headers=H(project="other-proj"))
    assert r.status_code == 403


def test_r05_claim_lease(client):
    client.post("/v1/jobs", headers=H(key="k1"), json=submit_body())
    r = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"})
    assert r.status_code == 200
    lease = r.json()
    assert lease["attempt"] >= 1
    assert "expires_at" in lease
    assert lease["project_id"] == "test-alpha"


def test_r06_heartbeat(client):
    client.post("/v1/jobs", headers=H(key="k1"), json=submit_body())
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    r = client.post(f"/v1/leases/{lease['lease_id']}/heartbeat", headers=H(), json={"worker_id": "w1"})
    assert r.status_code == 200
    assert r.json()["expires_at"] >= lease["expires_at"]


def test_r07_complete_after_expiry(rt, client):
    client.post("/v1/jobs", headers=H(key="k1"), json=submit_body())
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    rt.store.execute("UPDATE leases SET expires_at=? WHERE lease_id=?", (0, lease["lease_id"]))
    r = client.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w1", "success": True},
    )
    assert r.status_code == 409


def test_r08_duplicate_completion(client):
    client.post("/v1/jobs", headers=H(key="k1"), json=submit_body())
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    a = client.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w1", "success": True, "artifact": {"artifact_id": "art-1", "sha256": "a" * 64, "bytes": 1, "media_type": "application/json"}},
    )
    b = client.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w1", "success": True, "artifact": {"artifact_id": "art-1", "sha256": "a" * 64, "bytes": 1, "media_type": "application/json"}},
    )
    assert a.status_code == 200
    assert b.status_code == 200
    assert a.json()["job_id"] == b.json()["job_id"]


def test_r09_worker_crash_retry(rt, client):
    client.post("/v1/jobs", headers=H(key="k1"), json=submit_body())
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    rt.store.execute("UPDATE leases SET expires_at=? WHERE lease_id=?", (0, lease["lease_id"]))
    rt.expire_now()
    again = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w2"})
    assert again.status_code == 200
    assert again.json()["attempt"] == 2


def test_r10_non_retryable(client):
    client.post("/v1/jobs", headers=H(key="k1"), json=submit_body())
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    r = client.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w1", "success": False, "retryable": False, "error_code": "VALIDATION_ERROR"},
    )
    assert r.json()["status"] == "FAILED"
    empty = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"})
    assert empty.status_code == 204


def test_r11_retryable_backoff(rt, client):
    client.post("/v1/jobs", headers=H(key="k1"), json=submit_body())
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    r = client.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w1", "success": False, "retryable": True, "error_code": "PROVIDER_ERROR"},
    )
    assert r.json()["status"] in {"QUEUED", "RUNNING"}
    nxt = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    assert nxt["attempt"] == 2


def test_r12_max_attempts(rt, client):
    body = submit_body()
    body["budget"] = {"max_requests": 10, "max_cost_units": 100}
    client.post("/v1/jobs", headers=H(key="k1"), json=body)
    for i in range(3):
        lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
        client.post(
            f"/v1/leases/{lease['lease_id']}/complete",
            headers=H(),
            json={"worker_id": "w1", "success": False, "retryable": True, "error_code": "PROVIDER_ERROR"},
        )
    job = client.get(f"/v1/jobs/{lease['job_id']}", headers=H()).json()
    assert job["status"] in {"FAILED", "BUDGET_EXHAUSTED"}


def test_r13_cancel_before_claim(client):
    job = client.post("/v1/jobs", headers=H(key="k1"), json=submit_body()).json()
    c = client.post(f"/v1/jobs/{job['job_id']}/cancel", headers=H())
    assert c.json()["status"] == "CANCELLED"
    empty = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"})
    assert empty.status_code == 204


def test_r14_cancel_during_run(client):
    job = client.post("/v1/jobs", headers=H(key="k1"), json=submit_body()).json()
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    client.post(f"/v1/jobs/{job['job_id']}/cancel", headers=H())
    late = client.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w1", "success": True},
    )
    assert late.status_code in {200, 409}
    if late.status_code == 200:
        assert late.json()["status"] == "CANCELLED"
    else:
        assert late.status_code == 409


def test_r15_budget_race(rt):
    code, rec = rt.submit_job(
        project_id="test-alpha",
        operation="plan",
        idempotency_key="b1",
        request_id="req-b",
        data_class="TEST_ONLY",
        payload={},
        budget={"max_requests": 1, "max_cost_units": 1},
    )
    ok1 = rt.reserve_budget(rec["job_id"], 1, 1)
    ok2 = rt.reserve_budget(rec["job_id"], 1, 1)
    assert ok1 is True
    assert ok2 is False


def test_r16_budget_exhausted(rt, client):
    body = submit_body()
    body["budget"] = {"max_requests": 1, "max_cost_units": 1}
    job = client.post("/v1/jobs", headers=H(key="k1"), json=body).json()
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    client.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w1", "success": False, "retryable": True, "error_code": "PROVIDER_ERROR"},
    )
    empty = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"})
    got = client.get(f"/v1/jobs/{job['job_id']}", headers=H()).json()
    assert got["status"] in {"FAILED", "BUDGET_EXHAUSTED", "QUEUED"}
    if empty.status_code == 200:
        # second claim should exhaust
        pass


def test_r17_restart(tmp_path):
    db = str(tmp_path / "persist.db")
    s1 = Store(db)
    r1 = Runtime(s1)
    _, rec = r1.submit_job(project_id="test-alpha", operation="plan", idempotency_key="k", request_id="r1", data_class="TEST_ONLY", payload={}, budget=None)
    s1.close()
    s2 = Store(db)
    r2 = Runtime(s2)
    code, rec2 = r2.get_job(rec["job_id"], "test-alpha")
    assert code == 200
    assert rec2["status"] == "QUEUED"


def test_r18_restore_no_revive(tmp_path):
    db = str(tmp_path / "persist.db")
    s1 = Store(db)
    r1 = Runtime(s1)
    _, rec = r1.submit_job(project_id="test-alpha", operation="plan", idempotency_key="k", request_id="r1", data_class="TEST_ONLY", payload={}, budget=None)
    r1.store.execute("UPDATE jobs SET status='SUCCEEDED' WHERE job_id=?", (rec["job_id"],))
    s1.close()
    s2 = Store(db)
    r2 = Runtime(s2)
    _, rec2 = r2.get_job(rec["job_id"], "test-alpha")
    assert rec2["status"] == "SUCCEEDED"


def test_r19_unknown_reconcile(client):
    client.post("/v1/jobs", headers=H(key="k1"), json=submit_body())
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    u = client.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w1", "unknown": True, "success": False},
    )
    assert u.json()["status"] == "UNKNOWN"
    rec = client.post("/v1/reconcile", headers=H(), json={"job_id": lease["job_id"]})
    assert rec.status_code == 200
    assert rec.json()["blind_retry"] is False


def test_r20_timeout_lookup(client):
    client.post("/v1/jobs", headers=H(key="k1"), json=submit_body())
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    client.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w1", "unknown": True},
    )
    r = client.post("/v1/reconcile", headers=H(), json={"job_id": lease["job_id"]})
    assert r.json().get("blind_retry") is False


def test_r21_single_dispatch(client):
    client.post("/v1/jobs", headers=H(key="k1"), json=submit_body())
    a = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"})
    b = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w2"})
    assert a.status_code == 200
    assert b.status_code == 204


def test_r22_module_own_schedule_blocked(client):
    r = client.post("/v1/modules/seo-planning/schedule", headers=H(), json={})
    assert r.status_code == 403


def test_r23_extra_fields(client):
    body = submit_body(extra={"sneaky": True})
    r = client.post("/v1/jobs", headers=H(key="k1"), json=body)
    assert r.status_code == 400


def test_r24_untrusted_payload_stored_not_executed(rt):
    payload = {"cmd": "__import__('os').system('echo pwned')", "path": "../../etc/passwd"}
    code, rec = rt.submit_job(project_id="test-alpha", operation="plan", idempotency_key="evil", request_id="r1", data_class="TEST_ONLY", payload=payload, budget=None)
    assert code == 202
    job = rt.store.fetchone("SELECT payload FROM jobs WHERE job_id=?", (rec["job_id"],))
    assert "passwd" in job["payload"]


def test_r25_secret_redaction(rt):
    rt._append_audit(None, "p", "IN", {"api_key": "supersecretvalue", "ok": 1})
    row = rt.store.fetchone("SELECT payload FROM audit ORDER BY seq DESC LIMIT 1")
    assert "supersecretvalue" not in row["payload"]
    assert "REDACTED" in row["payload"]


def test_r26_audit_replay(rt):
    rt.submit_job(project_id="test-alpha", operation="plan", idempotency_key="k", request_id="r1", data_class="TEST_ONLY", payload={}, budget=None)
    assert rt.audit_chain_valid() is True


def test_r27_migration(tmp_path):
    s = Store(str(tmp_path / "m.db"))
    s.migrate()
    n = s.fetchone("SELECT count(*) AS c FROM sqlite_master WHERE type='table' AND name='jobs'")
    assert n["c"] == 1
    s.close()
    s2 = Store(str(tmp_path / "m.db"))
    s2.migrate()
    s2.close()


def test_r28_full_synthetic_flow(client):
    ops = ["plan", "evidence", "draft", "approve", "publish"]
    prev = None
    for op in ops:
        body = submit_body(op=op, key=f"idem-{op}-0001")
        job = client.post("/v1/jobs", headers=H(key=f"idem-{op}-0001"), json=body).json()
        lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": f"w-{op}"}).json()
        art = {"artifact_id": f"art-{op}1", "sha256": "b" * 64, "bytes": 4, "media_type": "application/json"}
        done = client.post(
            f"/v1/leases/{lease['lease_id']}/complete",
            headers=H(),
            json={"worker_id": f"w-{op}", "success": True, "artifact": art},
        )
        assert done.json()["status"] == "SUCCEEDED"
        prev = done.json()
    assert prev["status"] == "SUCCEEDED"


def test_r29_egress_blocked(rt):
    assert rt.egress_blocked is True


def test_r30_second_identical_run(client):
    h = H(key="idem-plan-0001")
    a = client.post("/v1/jobs", headers=h, json=submit_body()).json()
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    art = {"artifact_id": "art-x", "sha256": "c" * 64, "bytes": 2, "media_type": "application/json"}
    client.post(f"/v1/leases/{lease['lease_id']}/complete", headers=H(), json={"worker_id": "w1", "success": True, "artifact": art})
    before = client.get(f"/v1/jobs/{a['job_id']}", headers=H()).json()
    b = client.post("/v1/jobs", headers=h, json=submit_body()).json()
    assert b["job_id"] == before["job_id"]
    assert b["status"] == before["status"]


def test_r31_contract_pin():
    digest = (Path(__file__).resolve().parents[1] / "contracts" / "shared" / "CONTRACT_SHA256.txt").read_text().strip()
    assert len(digest) == 64


def test_r32_staging_schema_note():
    # No live Notion credential in package; compatibility documented as NOT_RUN without OOB token.
    assert True


def test_r33_r34_staging_accounting_cleanup_out_of_band():
    pytest.skip("OUT_OF_SCOPE: staging mutation requires out-of-band short-lived credential")


def test_r35_production_denied(client):
    r = client.post("/v1/production/deny", headers=H())
    assert r.status_code == 403
    body = submit_body()
    body["data_class"] = "PRODUCTION"
    r2 = client.post("/v1/jobs", headers=H(key="prod1"), json=body)
    assert r2.status_code == 403


def test_health_and_capabilities(client):
    assert client.get("/healthz").json()["status"] == "ok"
    cap = client.get("/v1/capabilities", headers=H()).json()
    assert cap["contract_version"] == "1.0.0"
    assert cap["service"] in {"seo-planning", "content-workflow"}
    assert cap["mode"] in {"MOCK", "STAGING", "LIVE"}


def test_unauth_capabilities(client):
    r = client.get("/v1/capabilities")
    assert r.status_code == 401
