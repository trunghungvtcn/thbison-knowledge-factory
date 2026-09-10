from __future__ import annotations

import os
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from . import CODE_COMMIT
from .contract_pin import ContractPinError, load_contract_pin
from .ranking import benchmark, rank
from .store import STORE
from .util import FORBIDDEN_WRITE, SAFE_NAME, TRAVERSAL, canonical_json, safe_basename, sha256_bytes, sha256_text, snapshot_hash

CONTRACT_VERSION = "1.0.0"
try:
    CONTRACT_SHA256 = load_contract_pin()
except ContractPinError as exc:  # fail closed at import for missing pin
    CONTRACT_SHA256 = None
    CONTRACT_PIN_ERROR = exc
else:
    CONTRACT_PIN_ERROR = None
POLICY_VERSION = "test-policy-1"
FORBIDDEN_STATUS = {"HOLD", "REVOKED", "REVIEW_REQUIRED"}
ALLOW_PRODUCTION = os.getenv("ALLOW_PRODUCTION", "false").lower() == "true"
APP_MODE = os.getenv("APP_MODE", "MOCK")

app = FastAPI(title="THBISON Vendor 4 Knowledge + Asset Gateway", version="1.0.0")


def now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def require_contract(x_contract_version: str | None) -> None:
    if x_contract_version and x_contract_version != CONTRACT_VERSION:
        raise HTTPException(status_code=400, detail={"code": "UNSUPPORTED_CONTRACT", "message": "unsupported"})


def auth_ok(authorization: str | None) -> bool:
    if authorization is None:
        return False
    if "PRODUCTION" in authorization.upper() and not ALLOW_PRODUCTION:
        raise HTTPException(status_code=403, detail={"code": "PRODUCTION_DENIED", "message": "production credential rejected"})
    return authorization.startswith("Bearer ")


def idem_get(key: str | None, payload_hash: str):
    if not key:
        return None
    rec = STORE.idempotency.get(key)
    if rec and rec["hash"] != payload_hash:
        raise HTTPException(status_code=409, detail={"code": "IDEMPOTENCY_CONFLICT"})
    return rec


def idem_put(key: str | None, payload_hash: str, status: int, body: Any):
    if key:
        STORE.idempotency[key] = {"hash": payload_hash, "status": status, "body": body}


@app.middleware("http")
async def bind_project(request: Request, call_next):
    if STORE.rate["force_429"]:
        STORE.rate["force_429"] = False
        return JSONResponse({"code": "RATE_LIMITED", "message": "retry"}, status_code=429, headers={"Retry-After": "1"})
    return await call_next(request)


@app.get("/healthz")
def healthz():
    return {"status": "ok"}


@app.get("/capabilities")
@app.get("/v1/capabilities")
def capabilities(authorization: str | None = Header(default=None), x_contract_version: str | None = Header(default=None)):
    require_contract(x_contract_version)
    if not auth_ok(authorization):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})
    if CONTRACT_PIN_ERROR is not None or not CONTRACT_SHA256:
        raise HTTPException(
            status_code=500,
            detail={"code": getattr(CONTRACT_PIN_ERROR, "code", "CONTRACT_PIN_MISSING"), "message": str(CONTRACT_PIN_ERROR or "pin missing")},
        )
    return {
        "contract_version": CONTRACT_VERSION,
        "service": "content-workflow",
        "code_commit": CODE_COMMIT,
        "contract_sha256": CONTRACT_SHA256,
        "mode": APP_MODE,
        "enabled_operations": [
            "knowledge.query",
            "evidence.read",
            "assets.upload",
            "assets.complete",
            "assets.read",
            "assets.refresh",
            "cache.invalidate",
        ],
        "max_json_bytes": 2097152,
    }


def scope_match(row: dict, q: dict) -> tuple[bool, str]:
    for key in ("project_id", "product_id", "model", "jurisdiction", "locale"):
        if q.get(key) and row.get(key) != q[key]:
            return False, f"SCOPE_MISMATCH_{key.upper()}"
    if q.get("revision") and q["revision"] != STORE.revision:
        return False, "STALE_REVISION"
    return True, "OK"


def usable(row: dict) -> tuple[bool, str]:
    if row.get("claim_id") in STORE.hold_claims or row.get("status") == "HOLD":
        return False, "HOLD_BLOCKED"
    if row.get("source_sha256") in STORE.revoked_sources or row.get("status") == "REVOKED":
        return False, "REVOKED_BLOCKED"
    if row.get("status") in FORBIDDEN_STATUS:
        return False, "STATUS_BLOCKED"
    if not row.get("locator"):
        return False, "MISSING_LOCATOR"
    expected = sha256_text(row.get("quote", ""))
    if row.get("quote_sha256") and row["quote_sha256"] != expected:
        return False, "QUOTE_HASH_MISMATCH"
    cond = row.get("conditions") or {}
    if cond.get("type") == "AMBIGUOUS" or cond.get("conflict"):
        return False, "CONDITION_CONFLICT"
    return True, "ELIGIBLE_IN_SCOPE"


def cache_key(q: dict) -> str:
    return canonical_json(
        {
            "project_id": q.get("project_id"),
            "product_id": q.get("product_id"),
            "model": q.get("model"),
            "jurisdiction": q.get("jurisdiction"),
            "locale": q.get("locale"),
            "revision": q.get("revision") or STORE.revision,
            "policy": POLICY_VERSION,
        }
    )


@app.post("/v1/knowledge/query")
def knowledge_query(
    body: dict,
    authorization: str | None = Header(default=None),
    x_contract_version: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    require_contract(x_contract_version)
    if not auth_ok(authorization):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})
    ph = sha256_text(canonical_json(body))
    existing = idem_get(idempotency_key, ph)
    if existing:
        return JSONResponse(existing["body"], status_code=existing["status"])

    project_id = body.get("project_id")
    if not project_id:
        raise HTTPException(status_code=400, detail={"code": "MISSING_PROJECT"})

    ck = cache_key(body)
    cached = STORE.cache.get(ck)
    if cached and cached.get("revision") == STORE.revision:
        resp = cached["body"]
        resp = dict(resp)
        resp["cache"] = "HIT"
        idem_put(idempotency_key, ph, 200, resp)
        return resp

    selected = []
    blockers = []
    seen = set()
    for row in STORE.knowledge:
        ok, reason = scope_match(row, body)
        if not ok:
            if body.get("project_id") and row.get("project_id") != body["project_id"]:
                continue
            blockers.append({"claim_id": row["claim_id"], "reason": reason})
            continue
        uok, ureason = usable(row)
        key = (row["claim_id"], str(row.get("claim_version")))
        if key in seen:
            continue
        seen.add(key)
        if not uok:
            blockers.append({"claim_id": row["claim_id"], "reason": ureason})
            continue
        selected.append(row)

    ranked = rank(selected)
    claims = []
    for r in ranked:
        claims.append(
            {
                "claim_id": r["claim_id"],
                "text": r["quote"],
                "status": "ELIGIBLE",
                "risk": "DESCRIPTIVE",
                "allowed_uses": ["DRAFT"],
                "source_ref": "synthetic-source",
                "source_version": str(r.get("claim_version", "1")),
                "source_sha256": r["source_sha256"],
                "locator": r["locator"],
                "quote": r["quote"],
                "quote_sha256": r["quote_sha256"],
                "applicability": "SYNTHETIC TEST_ONLY",
                "jurisdiction": r.get("jurisdiction", "TEST_ONLY"),
            }
        )

    gaps = [f"{b['claim_id']}:{b['reason']}" for b in blockers]
    bundle_id = "b-" + sha256_text(ck)[:16]
    bundle = {
        "contract_version": CONTRACT_VERSION,
        "project_id": project_id,
        "data_class": "TEST_ONLY",
        "bundle_id": bundle_id,
        "snapshot_sha256": "0" * 64,
        "policy_version": POLICY_VERSION,
        "as_of": now_iso(),
        "claims": claims,
        "gaps": gaps,
    }
    bundle["snapshot_sha256"] = snapshot_hash(bundle)
    STORE.bundles[bundle_id] = bundle
    STORE.cache[ck] = {"revision": STORE.revision, "body": {"bundle": bundle, "blockers": blockers, "ranking": [{"claim_id": r["claim_id"], "score": r["rank_score"], "reason": r["rank_reason"]} for r in ranked], "cache": "MISS", "data_class": "TEST_ONLY"}}
    out = STORE.cache[ck]["body"]
    # wrong project explicit 403 if no rows in other projects match requested and request project unknown
    known_projects = {r["project_id"] for r in STORE.knowledge}
    if project_id not in known_projects:
        raise HTTPException(status_code=403, detail={"code": "WRONG_SCOPE", "message": "unknown or forbidden project", "reason": "WRONG_PROJECT"})
    idem_put(idempotency_key, ph, 200, out)
    return out


@app.get("/v1/evidence/{bundle_id}")
def get_bundle(bundle_id: str, authorization: str | None = Header(default=None)):
    if not auth_ok(authorization):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})
    b = STORE.bundles.get(bundle_id)
    if not b:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    return b


@app.post("/v1/assets/uploads")
def start_upload(
    body: dict,
    authorization: str | None = Header(default=None),
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
):
    if not auth_ok(authorization):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})
    project_id = body.get("project_id")
    filename = body.get("filename")
    size = int(body.get("size") or 0)
    declared = body.get("sha256")
    if not project_id or not filename:
        raise HTTPException(status_code=400, detail={"code": "INVALID"})
    try:
        filename = safe_basename(filename)
    except ValueError:
        raise HTTPException(status_code=400, detail={"code": "PATH_TRAVERSAL"})
    content = body.get("content_b64")
    raw = b""
    if content:
        import base64

        raw = base64.b64decode(content)
    elif "content" in body and isinstance(body["content"], str):
        raw = body["content"].encode("utf-8")
    else:
        raw = b"SYNTHETIC_TEST_ONLY_BLOB_" + filename.encode()
    digest = sha256_bytes(raw)
    if len(raw) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail={"code": "ARCHIVE_BOMB_POLICY"})
    if declared and declared != digest and declared != "TO_BE_COMPUTED_BY_SIMULATOR":
        raise HTTPException(status_code=400, detail={"code": "HASH_MISMATCH"})
    # basename collision: same name different hash
    for a in STORE.assets.values():
        if a.get("filename") == filename and a.get("project_id") == project_id and a.get("sha256") not in (None, "TO_BE_COMPUTED_BY_SIMULATOR", digest):
            raise HTTPException(status_code=409, detail={"code": "BASENAME_COLLISION"})
    # duplicate: same hash -> same logical asset
    for a in STORE.assets.values():
        if a.get("sha256") == digest and a.get("project_id") == project_id and a.get("state") == "VERIFIED":
            return {"upload_id": a.get("upload_id", a["asset_id"]), "asset_id": a["asset_id"], "state": "DUPLICATE_EXISTING", "sha256": digest, "data_class": "TEST_ONLY"}
    upload_id = "up-" + uuid.uuid4().hex[:12]
    asset_id = "ast-" + digest[:12]
    rec = {
        "upload_id": upload_id,
        "asset_id": asset_id,
        "project_id": project_id,
        "filename": filename,
        "size": len(raw) if raw else size,
        "sha256": digest,
        "state": "PENDING_UPLOAD",
        "data_class": "TEST_ONLY",
        "signed_url": f"sim://signed/{upload_id}?exp={int(time.time())+3600}",
        "expires_at": int(time.time()) + 3600,
    }
    STORE.persist_upload(rec, raw)
    return {"upload_id": upload_id, "asset_id": asset_id, "state": "PENDING_UPLOAD", "signed_url": rec["signed_url"], "sha256": digest, "data_class": "TEST_ONLY"}


@app.post("/v1/assets/uploads/{upload_id}/complete")
def complete_upload(upload_id: str, body: dict | None = None, authorization: str | None = Header(default=None)):
    if not auth_ok(authorization):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})
    rec = STORE.uploads.get(upload_id)
    if not rec:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    raw = STORE.blobs.get(upload_id)
    if raw is None:
        raise HTTPException(status_code=409, detail={"code": "MISSING_BLOB"})
    digest = sha256_bytes(raw)
    if rec["sha256"] != digest:
        raise HTTPException(status_code=400, detail={"code": "HASH_MISMATCH"})
    if body and body.get("sha256") and body["sha256"] != digest:
        raise HTTPException(status_code=400, detail={"code": "HASH_MISMATCH"})
    rec["state"] = "VERIFIED"
    rec["verified_at"] = now_iso()
    STORE.persist_upload(rec, raw)
    return {"asset_id": rec["asset_id"], "state": "VERIFIED", "sha256": digest, "size": rec["size"], "data_class": "TEST_ONLY"}


@app.get("/v1/assets/{asset_id}")
def get_asset(asset_id: str, project_id: str | None = None, authorization: str | None = Header(default=None)):
    if not auth_ok(authorization):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})
    rec = STORE.assets.get(asset_id)
    if not rec:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    if project_id and rec.get("project_id") != project_id:
        raise HTTPException(status_code=403, detail={"code": "CROSS_PROJECT"})
    return rec


@app.post("/v1/assets/{asset_id}/refresh")
def refresh_asset(asset_id: str, authorization: str | None = Header(default=None)):
    if not auth_ok(authorization):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})
    rec = STORE.assets.get(asset_id)
    if not rec:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND"})
    rec["signed_url"] = f"sim://signed/{rec.get('upload_id', asset_id)}?exp={int(time.time())+3600}"
    rec["expires_at"] = int(time.time()) + 3600
    return {"asset_id": asset_id, "signed_url": rec["signed_url"], "sha256": rec.get("sha256"), "identity_unchanged": True, "data_class": "TEST_ONLY"}


@app.post("/v1/cache/invalidate")
def invalidate(body: dict, authorization: str | None = Header(default=None)):
    if not auth_ok(authorization):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})
    reason = body.get("reason")
    if body.get("revision"):
        STORE.revision = body["revision"]
    if body.get("revoke_source"):
        STORE.revoked_sources.add(body["revoke_source"])
    if body.get("hold_claim"):
        STORE.hold_claims.add(body["hold_claim"])
    if reason in ("REVOKE", "HOLD", "NEW_REVISION") or body.get("project_id"):
        STORE.cache.clear()
    return {"invalidated": True, "revision": STORE.revision, "data_class": "TEST_ONLY"}


@app.post("/v1/admin/write")
def admin_write(body: dict, authorization: str | None = Header(default=None)):
    if not auth_ok(authorization):
        raise HTTPException(status_code=401, detail={"code": "UNAUTHORIZED"})
    fields = body.get("fields") or {}
    for k in fields:
        if k in FORBIDDEN_WRITE:
            raise HTTPException(status_code=403, detail={"code": "HUMAN_MANAGED_FIELD"})
        if k not in {"title", "note_internal", "locator", "quote"}:
            raise HTTPException(status_code=400, detail={"code": "UNKNOWN_WRITE_FIELD"})
    run_id = os.getenv("TEST_RUN_ID") or "test-run-local"
    STORE.mutations.append({"test_run_id": run_id, "fields": fields, "ts": now_iso()})
    return {"ok": True, "test_run_id": run_id, "receipt_id": "mut-" + sha256_text(canonical_json(fields))[:12]}


@app.post("/v1/sim/force-429")
def force_429():
    STORE.rate["force_429"] = True
    return {"ok": True}


@app.get("/v1/sim/ranking-benchmark")
def ranking_bench():
    ids = [r["claim_id"] for r in rank([k for k in STORE.knowledge if k["status"] == "ELIGIBLE"])]
    return {"baseline": ids, "candidate": ids, "decision": benchmark(ids, ids), "data_class": "TEST_ONLY"}
