"""Forged identity, project isolation, expiry, duplicate complete (MOCK auth boundary)."""
from __future__ import annotations

from app.runtime import Runtime
from app.store import Store
from tests.http_client import make_http


def client(tmp_path):
    c, _ = make_http(Runtime(Store(str(tmp_path / "a.db"))))
    return c


def H(project="test-alpha", svc="runtime", key=None, extra=None):
    h = {
        "X-Service-Id": svc,
        "X-Project-Id": project,
        "X-Roles": "orchestrator",
        "X-Contract-Version": "1.0.0",
        "X-Request-Id": "req-iso-1",
    }
    if key:
        h["Idempotency-Key"] = key
    if extra:
        h.update(extra)
    return h


BODY = {
    "project_id": "test-alpha",
    "operation": "plan",
    "idempotency_key": "idem-iso",
    "request_id": "req-iso-1",
    "data_class": "TEST_ONLY",
    "payload": {},
    "budget": {"max_requests": 4, "max_cost_units": 20},
}


def test_missing_service_header_unauthorized(tmp_path):
    c = client(tmp_path)
    r = c.post("/v1/jobs", headers={"X-Project-Id": "test-alpha", "Idempotency-Key": "k"}, json=BODY)
    assert r.status_code == 401


def test_forged_project_header_rejected_on_read(tmp_path):
    c = client(tmp_path)
    job = c.post("/v1/jobs", headers=H(key="k1"), json=BODY).json()
    r = c.get(f"/v1/jobs/{job['job_id']}", headers=H(project="forged-project"))
    assert r.status_code == 403
    # caller asserting another project in body vs header
    body2 = dict(BODY)
    body2["project_id"] = "other"
    r2 = c.post("/v1/jobs", headers=H(key="k2"), json=body2)
    assert r2.status_code == 403


def test_wrong_worker_cannot_complete(tmp_path):
    c = client(tmp_path)
    c.post("/v1/jobs", headers=H(key="k1"), json=BODY)
    lease = c.post("/v1/leases/claim", headers=H(), json={"worker_id": "w-real"}).json()
    r = c.post(
        f"/v1/leases/{lease['lease_id']}/complete",
        headers=H(),
        json={"worker_id": "w-forged", "success": True},
    )
    assert r.status_code == 403


def test_duplicate_completion_same_receipt(tmp_path):
    c = client(tmp_path)
    c.post("/v1/jobs", headers=H(key="k1"), json=BODY)
    lease = c.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    payload = {
        "worker_id": "w1",
        "success": True,
        "artifact": {"artifact_id": "art-1", "sha256": "a" * 64, "bytes": 1, "media_type": "application/json"},
    }
    a = c.post(f"/v1/leases/{lease['lease_id']}/complete", headers=H(), json=payload)
    b = c.post(f"/v1/leases/{lease['lease_id']}/complete", headers=H(), json=payload)
    assert a.status_code == 200 and b.status_code == 200
    assert a.json()["job_id"] == b.json()["job_id"]
    assert a.json()["status"] == b.json()["status"] == "SUCCEEDED"


def test_expiry_then_reclaim(tmp_path):
    rt = Runtime(Store(str(tmp_path / "e.db")))
    c, _ = make_http(rt)
    c.post("/v1/jobs", headers=H(key="k1"), json=BODY)
    lease = c.post("/v1/leases/claim", headers=H(), json={"worker_id": "w1"}).json()
    rt.store.execute("UPDATE leases SET expires_at=0 WHERE lease_id=?", (lease["lease_id"],))
    late = c.post(f"/v1/leases/{lease['lease_id']}/complete", headers=H(), json={"worker_id": "w1", "success": True})
    assert late.status_code == 409
    rt.expire_now()
    nxt = c.post("/v1/leases/claim", headers=H(), json={"worker_id": "w2"})
    assert nxt.status_code == 200
    assert nxt.json()["attempt"] == 2
