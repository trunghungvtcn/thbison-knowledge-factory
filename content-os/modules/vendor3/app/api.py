"""HTTP adapter for Vendor 3 runtime."""
from __future__ import annotations

import os
from typing import Any

from fastapi import FastAPI, Header, Request, Response
from fastapi.responses import JSONResponse

from . import CODE_COMMIT, CONTRACT_SHA256, CONTRACT_VERSION
from .runtime import Runtime
from .store import Store

store = Store(os.getenv("DATABASE_URL", "file:/tmp/thbison-runtime.db").replace("sqlite:///", ""))
if store.path.startswith("file:"):
    store.close()
    store = Store("/tmp/thbison-runtime.db")
runtime = Runtime(store)


def create_app(rt: Runtime | None = None) -> FastAPI:
    app = FastAPI(title="THBISON Vendor 3 Runtime", version="1.0.0")
    r = rt or runtime

    def auth(x_service_id: str | None, x_project_id: str | None, x_roles: str | None, x_contract_version: str | None) -> tuple[int, dict] | None:
        if x_contract_version and x_contract_version != CONTRACT_VERSION:
            return 400, r._err("na", "UNSUPPORTED_CONTRACT", "unsupported contract version", False)
        if not x_service_id or not x_project_id:
            return 401, r._err("na", "UNAUTHORIZED", "service identity required", False)
        return None

    @app.get("/healthz")
    def healthz() -> dict:
        return {"status": "ok"}

    @app.get("/v1/capabilities")
    def capabilities(
        x_service_id: str | None = Header(default=None),
        x_project_id: str | None = Header(default=None),
        x_roles: str | None = Header(default=None),
        x_contract_version: str | None = Header(default=None),
    ) -> Any:
        err = auth(x_service_id, x_project_id, x_roles, x_contract_version)
        if err:
            return JSONResponse(err[1], status_code=err[0])
        return {
            "contract_version": CONTRACT_VERSION,
            "service": "content-workflow",
            "code_commit": CODE_COMMIT,
            "contract_sha256": CONTRACT_SHA256,
            "mode": r.mode if r.mode in {"MOCK", "STAGING", "LIVE"} else "MOCK",
            "enabled_operations": ["plan", "draft", "evidence", "approve", "publish", "lease", "reconcile"],
            "max_json_bytes": 2097152,
        }

    @app.post("/v1/jobs")
    async def submit(request: Request) -> Any:
        headers = request.headers
        err = auth(headers.get("x-service-id"), headers.get("x-project-id"), headers.get("x-roles"), headers.get("x-contract-version"))
        if err:
            return JSONResponse(err[1], status_code=err[0])
        body = await request.json()
        extra = any(k not in {"project_id", "operation", "idempotency_key", "request_id", "data_class", "payload", "budget"} for k in body)
        if "idempotency-key" not in {h.lower() for h in headers.keys()} and not body.get("idempotency_key"):
            return JSONResponse(r._err(body.get("request_id", "na"), "VALIDATION_ERROR", "Idempotency-Key required", False), status_code=400)
        project = headers.get("x-project-id")
        if body.get("project_id") and body["project_id"] != project:
            return JSONResponse(r._err(body.get("request_id", "na"), "FORBIDDEN", "project binding mismatch", False), status_code=403)
        code, data = r.submit_job(
            project_id=project,
            operation=body.get("operation", ""),
            idempotency_key=headers.get("idempotency-key") or body.get("idempotency_key", ""),
            request_id=headers.get("x-request-id") or body.get("request_id", "req-missing"),
            data_class=body.get("data_class", "TEST_ONLY"),
            payload=body.get("payload") or {},
            budget=body.get("budget"),
            extra_fields=extra,
        )
        return JSONResponse(data, status_code=code)

    @app.get("/v1/jobs/{job_id}")
    def get_job(job_id: str, x_project_id: str | None = Header(default=None), x_service_id: str | None = Header(default=None), x_roles: str | None = Header(default=None), x_contract_version: str | None = Header(default=None)) -> Any:
        err = auth(x_service_id, x_project_id, x_roles, x_contract_version)
        if err:
            return JSONResponse(err[1], status_code=err[0])
        code, data = r.get_job(job_id, x_project_id)
        return JSONResponse(data, status_code=code)

    @app.post("/v1/jobs/{job_id}/cancel")
    def cancel(job_id: str, x_project_id: str | None = Header(default=None), x_service_id: str | None = Header(default=None), x_roles: str | None = Header(default=None), x_contract_version: str | None = Header(default=None)) -> Any:
        err = auth(x_service_id, x_project_id, x_roles, x_contract_version)
        if err:
            return JSONResponse(err[1], status_code=err[0])
        code, data = r.cancel(job_id, x_project_id)
        return JSONResponse(data, status_code=code)

    @app.post("/v1/leases/claim")
    async def claim(request: Request) -> Any:
        headers = request.headers
        err = auth(headers.get("x-service-id"), headers.get("x-project-id"), headers.get("x-roles"), headers.get("x-contract-version"))
        if err:
            return JSONResponse(err[1], status_code=err[0])
        body = await request.json()
        code, data = r.claim(project_id=headers.get("x-project-id"), worker_id=body.get("worker_id", "worker-1"), request_id=body.get("request_id", "req-claim"))
        if code == 204:
            return Response(status_code=204)
        return JSONResponse(data, status_code=code)

    @app.post("/v1/leases/{lease_id}/heartbeat")
    async def heartbeat(lease_id: str, request: Request) -> Any:
        headers = request.headers
        err = auth(headers.get("x-service-id"), headers.get("x-project-id"), headers.get("x-roles"), headers.get("x-contract-version"))
        if err:
            return JSONResponse(err[1], status_code=err[0])
        body = await request.json()
        code, data = r.heartbeat(lease_id, headers.get("x-project-id"), body.get("worker_id", "worker-1"))
        return JSONResponse(data, status_code=code)

    @app.post("/v1/leases/{lease_id}/complete")
    async def complete(lease_id: str, request: Request) -> Any:
        headers = request.headers
        err = auth(headers.get("x-service-id"), headers.get("x-project-id"), headers.get("x-roles"), headers.get("x-contract-version"))
        if err:
            return JSONResponse(err[1], status_code=err[0])
        body = await request.json()
        code, data = r.complete(
            lease_id,
            headers.get("x-project-id"),
            body.get("worker_id", "worker-1"),
            success=body.get("success", True),
            retryable=body.get("retryable", False),
            error_code=body.get("error_code"),
            artifact=body.get("artifact"),
            unknown=body.get("unknown", False),
        )
        return JSONResponse(data, status_code=code)

    @app.post("/v1/reconcile")
    async def reconcile(request: Request) -> Any:
        headers = request.headers
        err = auth(headers.get("x-service-id"), headers.get("x-project-id"), headers.get("x-roles"), headers.get("x-contract-version"))
        if err:
            return JSONResponse(err[1], status_code=err[0])
        body = await request.json()
        code, data = r.reconcile(body.get("job_id", ""), headers.get("x-project-id"))
        return JSONResponse(data, status_code=code)

    @app.post("/v1/modules/{module}/schedule")
    def module_schedule(module: str, x_project_id: str | None = Header(default=None), x_service_id: str | None = Header(default=None)) -> Any:
        code, data = r.block_module_schedule(module)
        return JSONResponse(data, status_code=code)

    @app.post("/v1/production/deny")
    def prod_deny() -> Any:
        code, data = r.deny_production()
        return JSONResponse(data, status_code=code)

    return app


app = create_app()
