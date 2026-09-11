from __future__ import annotations

import base64
import hashlib
import importlib
import json
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.main import app
from app.store import STORE
from app.util import sha256_text

AUTH = {"Authorization": "Bearer test-token", "X-Contract-Version": "1.0.0"}
client = TestClient(app)


def reset():
    STORE.cache.clear()
    STORE.revoked_sources.clear()
    STORE.hold_claims.clear()
    STORE.revision = "rev-synthetic-1"
    STORE.rate["force_429"] = False


def test_k01_query_in_scope():
    reset()
    r = client.post(
        "/v1/knowledge/query",
        json={"project_id": "test-alpha", "product_id": "manual-hoist-demo", "model": "demo-1t", "jurisdiction": "VN", "locale": "vi-VN"},
        headers=AUTH,
    )
    assert r.status_code == 200
    body = r.json()
    assert body["bundle"]["contract_version"] == "1.0.0"
    assert body["bundle"]["data_class"] == "TEST_ONLY"
    assert any(c["claim_id"] == "syn-claim-001" for c in body["bundle"]["claims"])
    assert all(c["status"] == "ELIGIBLE" for c in body["bundle"]["claims"])


def test_k02_wrong_project():
    reset()
    r = client.post("/v1/knowledge/query", json={"project_id": "other-project"}, headers=AUTH)
    assert r.status_code == 403


def test_k03_wrong_jurisdiction():
    reset()
    r = client.post(
        "/v1/knowledge/query",
        json={"project_id": "test-alpha", "jurisdiction": "US"},
        headers=AUTH,
    )
    assert r.status_code == 200
    assert r.json()["bundle"]["claims"] == []


def test_k04_hold_blocked():
    reset()
    r = client.post("/v1/knowledge/query", json={"project_id": "test-alpha"}, headers=AUTH)
    ids = [c["claim_id"] for c in r.json()["bundle"]["claims"]]
    assert "syn-claim-002" not in ids
    assert any(b["reason"] in ("HOLD_BLOCKED", "CONDITION_CONFLICT") for b in r.json()["blockers"])


def test_k05_revoked_invalidates_cache():
    reset()
    q = {"project_id": "test-alpha"}
    r1 = client.post("/v1/knowledge/query", json=q, headers=AUTH)
    assert r1.status_code == 200
    src = STORE.knowledge[0]["source_sha256"]
    client.post("/v1/cache/invalidate", json={"reason": "REVOKE", "revoke_source": src}, headers=AUTH)
    r2 = client.post("/v1/knowledge/query", json=q, headers=AUTH)
    ids = [c["claim_id"] for c in r2.json()["bundle"]["claims"]]
    assert "syn-claim-001" not in ids


def test_k07_quote_tamper():
    reset()
    STORE.knowledge[0]["quote_sha256"] = "0" * 64
    r = client.post("/v1/knowledge/query", json={"project_id": "test-alpha"}, headers=AUTH)
    ids = [c["claim_id"] for c in r.json()["bundle"]["claims"]]
    assert "syn-claim-001" not in ids
    STORE.knowledge[0]["quote_sha256"] = sha256_text(STORE.knowledge[0]["quote"])


def test_k08_missing_locator():
    reset()
    old = STORE.knowledge[0]["locator"]
    STORE.knowledge[0]["locator"] = ""
    r = client.post("/v1/knowledge/query", json={"project_id": "test-alpha"}, headers=AUTH)
    ids = [c["claim_id"] for c in r.json()["bundle"]["claims"]]
    assert "syn-claim-001" not in ids
    STORE.knowledge[0]["locator"] = old


def test_k09_dedupe():
    reset()
    STORE.knowledge.append(dict(STORE.knowledge[0]))
    r = client.post("/v1/knowledge/query", json={"project_id": "test-alpha"}, headers=AUTH)
    ids = [c["claim_id"] for c in r.json()["bundle"]["claims"]]
    assert ids.count("syn-claim-001") == 1
    STORE.knowledge.pop()


def test_k11_ranking_replay():
    reset()
    a = client.post("/v1/knowledge/query", json={"project_id": "test-alpha"}, headers=AUTH).json()["ranking"]
    b = client.post("/v1/knowledge/query", json={"project_id": "test-alpha"}, headers=AUTH).json()["ranking"]
    # second may be cache hit; ranking list present on first
    r = client.get("/v1/sim/ranking-benchmark")
    assert r.json()["decision"] in ("NO_IMPROVEMENT", "PROMOTE")


def test_k13_k16_k17_upload():
    reset()
    payload = base64.b64encode(b"hello-synthetic").decode()
    digest = hashlib.sha256(b"hello-synthetic").hexdigest()
    r = client.post(
        "/v1/assets/uploads",
        json={"project_id": "test-alpha", "filename": "manual.pdf", "content_b64": payload, "sha256": digest},
        headers=AUTH,
    )
    assert r.status_code == 200
    assert r.json()["state"] == "PENDING_UPLOAD"
    uid = r.json()["upload_id"]
    aid = r.json()["asset_id"]
    bad = client.post(f"/v1/assets/uploads/{uid}/complete", json={"sha256": "ff" * 32}, headers=AUTH)
    assert bad.status_code == 400
    ok = client.post(f"/v1/assets/uploads/{uid}/complete", json={"sha256": digest}, headers=AUTH)
    assert ok.status_code == 200
    assert ok.json()["state"] == "VERIFIED"
    dup = client.post(
        "/v1/assets/uploads",
        json={"project_id": "test-alpha", "filename": "manual-copy.pdf", "content_b64": payload, "sha256": digest},
        headers=AUTH,
    )
    assert dup.json()["state"] == "DUPLICATE_EXISTING"


def test_k15_refresh_keeps_identity():
    reset()
    r = client.post("/v1/assets/uploads", json={"project_id": "test-alpha", "filename": "a.bin", "content": "x"}, headers=AUTH)
    aid = r.json()["asset_id"]
    sha = r.json()["sha256"]
    ref = client.post(f"/v1/assets/{aid}/refresh", headers=AUTH)
    assert ref.json()["identity_unchanged"] is True
    assert ref.json()["sha256"] == sha


def test_k18_basename_collision():
    reset()
    client.post("/v1/assets/uploads", json={"project_id": "test-alpha", "filename": "same.txt", "content": "aaa"}, headers=AUTH)
    r = client.post("/v1/assets/uploads", json={"project_id": "test-alpha", "filename": "same.txt", "content": "bbb"}, headers=AUTH)
    assert r.status_code == 409


def test_k19_path_traversal():
    r = client.post("/v1/assets/uploads", json={"project_id": "test-alpha", "filename": "../etc/passwd"}, headers=AUTH)
    assert r.status_code == 400


def test_k20_retry_after():
    client.post("/v1/sim/force-429")
    r = client.get("/healthz")
    assert r.status_code == 429
    assert r.headers.get("Retry-After") == "1"


def test_k21_k22_cache_revision():
    reset()
    q = {"project_id": "test-alpha"}
    a = client.post("/v1/knowledge/query", json=q, headers=AUTH)
    b = client.post("/v1/knowledge/query", json=q, headers=AUTH)
    assert b.json()["cache"] == "HIT"
    client.post("/v1/cache/invalidate", json={"reason": "NEW_REVISION", "revision": "rev-2"}, headers=AUTH)
    c = client.post("/v1/knowledge/query", json=q, headers=AUTH)
    assert c.json()["cache"] == "MISS"


def test_k24_k25_writes():
    r = client.post("/v1/admin/write", json={"fields": {"Status": "APPROVED"}}, headers=AUTH)
    assert r.status_code == 403
    r = client.post("/v1/admin/write", json={"fields": {"unknown_zzz": "x"}}, headers=AUTH)
    assert r.status_code == 400
    r = client.post("/v1/admin/write", json={"fields": {"title": "t"}}, headers=AUTH)
    assert r.status_code == 200
    assert r.json()["test_run_id"]


def test_k26_pending_blob_survives():
    reset()
    r = client.post("/v1/assets/uploads", json={"project_id": "test-alpha", "filename": "keep.bin", "content": "blob"}, headers=AUTH)
    uid = r.json()["upload_id"]
    assert uid in STORE.blobs
    snap = STORE.snapshot()
    assert snap["blobs"][uid]


def test_k27_cross_project():
    reset()
    r = client.post("/v1/assets/uploads", json={"project_id": "test-alpha", "filename": "p.bin", "content": "z"}, headers=AUTH)
    aid = r.json()["asset_id"]
    g = client.get(f"/v1/assets/{aid}", params={"project_id": "other"}, headers=AUTH)
    assert g.status_code == 403


def test_k36_production_token():
    r = client.post("/v1/knowledge/query", json={"project_id": "test-alpha"}, headers={"Authorization": "Bearer PRODUCTION"})
    assert r.status_code == 403


def test_health_and_caps():
    assert client.get("/healthz").status_code == 200
    r = client.get("/capabilities", headers=AUTH)
    assert r.status_code == 200
    assert r.json()["mode"] == "MOCK"


def test_k30_get_bundle():
    reset()
    r = client.post("/v1/knowledge/query", json={"project_id": "test-alpha"}, headers=AUTH)
    bid = r.json()["bundle"]["bundle_id"]
    g = client.get(f"/v1/evidence/{bid}", headers=AUTH)
    assert g.status_code == 200
    assert g.json()["bundle_id"] == bid


def test_k01_evidence_schema_and_gaps():
    import jsonschema

    reset()
    schema = json.loads((ROOT / "contracts/shared/schemas/EvidenceBundle.json").read_text())
    r = client.post("/v1/knowledge/query", json={"project_id": "test-alpha"}, headers=AUTH)
    bundle = r.json()["bundle"]
    jsonschema.validate(bundle, schema)
    assert any(g.startswith("syn-claim-002:") for g in bundle["gaps"])


def test_k19_symlink_and_bomb_policy():
    r = client.post("/v1/assets/uploads", json={"project_id": "test-alpha", "filename": "link\x00/x"}, headers=AUTH)
    assert r.status_code == 400
    r = client.post("/v1/assets/uploads", json={"project_id": "test-alpha", "filename": "/tmp/abs.bin"}, headers=AUTH)
    assert r.status_code == 400


def test_capabilities_pin_and_schema():
    import jsonschema

    schema = json.loads((ROOT / "contracts/shared/schemas/CapabilitiesReply.json").read_text())
    r = client.get("/capabilities", headers=AUTH)
    assert r.status_code == 200
    body = r.json()
    jsonschema.validate(body, schema)
    pin = (ROOT / "contracts/shared/CONTRACT_SHA256.txt").read_text().strip().split()[0]
    assert body["contract_sha256"] == pin
    assert body["contract_sha256"] != "0" * 64
