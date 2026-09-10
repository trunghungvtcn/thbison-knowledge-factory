"""HTTP-level tests through FastAPI (separate from in-process harness)."""
from __future__ import annotations

import pytest

from app.projection import project_receipt_status
from app.runtime import Runtime
from app.store import Store
from tests.http_client import make_http


@pytest.fixture()
def http(tmp_path):
    rt = Runtime(Store(str(tmp_path / "http.db")))
    client, _mode = make_http(rt)
    return client, rt


def H(project="test-alpha", key=None):
    h = {
        "X-Service-Id": "runtime",
        "X-Project-Id": project,
        "X-Roles": "orchestrator",
        "X-Contract-Version": "1.0.0",
        "X-Request-Id": "req-http-1",
    }
    if key:
        h["Idempotency-Key"] = key
    return h


def body(op="plan", key="idem-http-1"):
    return {
        "project_id": "test-alpha",
        "operation": op,
        "idempotency_key": key,
        "request_id": "req-http-1",
        "data_class": "TEST_ONLY",
        "payload": {"seed": "http"},
        "budget": {"max_requests": 4, "max_cost_units": 20},
    }


def test_http_health_unauthenticated(http):
    client, _ = http
    r = client.get("/healthz")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_http_capabilities_requires_auth(http):
    client, _ = http
    assert client.get("/v1/capabilities").status_code == 401
    cap = client.get("/v1/capabilities", headers=H()).json()
    assert cap["service"] == "content-workflow"
    assert cap["mode"] == "MOCK"


def test_http_enqueue_schema_rejection(http):
    client, _ = http
    r = client.post("/v1/jobs", headers=H(key="k1"), json={**body(), "sneaky": True})
    assert r.status_code == 400
    assert r.json()["code"] == "VALIDATION_ERROR"


def test_http_enqueue_lease_complete(http):
    client, _ = http
    r = client.post("/v1/jobs", headers=H(key="k1"), json=body())
    assert r.status_code == 202
    job = r.json()
    assert job["status"] == "QUEUED"
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"})
    assert lease.status_code == 200
    lid = lease.json()["lease_id"]
    hb = client.post(f"/v1/leases/{lid}/heartbeat", headers=H(), json={"worker_id": "w1"})
    assert hb.status_code == 200
    done = client.post(
        f"/v1/leases/{lid}/complete",
        headers=H(),
        json={
            "worker_id": "w1",
            "success": True,
            "artifact": {"artifact_id": "art-http", "sha256": "a" * 64, "bytes": 1, "media_type": "application/json"},
        },
    )
    assert done.status_code == 200
    assert done.json()["status"] == "SUCCEEDED"


def test_http_expiry_rejects_complete(http):
    client, rt = http
    client.post("/v1/jobs", headers=H(key="k1"), json=body())
    lease = client.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    rt.store.execute("UPDATE leases SET expires_at=? WHERE lease_id=?", (0, lease["lease_id"]))
    r = client.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w1", "success": True},
    )
    assert r.status_code == 409


def test_http_project_boundary(http):
    client, _ = http
    job = client.post("/v1/jobs", headers=H(key="k1"), json=body()).json()
    r = client.get(f"/v1/jobs/{job['job_id']}", headers=H(project="other-proj"))
    assert r.status_code == 403


def test_projection_leased_to_queued():
    assert project_receipt_status("LEASED") == "QUEUED"
    assert project_receipt_status("FAILED", "BUDGET_EXHAUSTED") == "BUDGET_EXHAUSTED"
