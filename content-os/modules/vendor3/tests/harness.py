"""Minimal in-process client so tests run without FastAPI installed."""
from __future__ import annotations

from typing import Any


class Resp:
    def __init__(self, status_code: int, data: Any):
        self.status_code = status_code
        self._data = data

    def json(self):
        return self._data


class Harness:
    def __init__(self, runtime):
        self.r = runtime

    def post(self, path: str, headers=None, json=None):
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        body = json or {}
        project = headers.get("x-project-id")
        svc = headers.get("x-service-id")
        if path != "/healthz" and not (svc and project):
            return Resp(401, self.r._err("na", "UNAUTHORIZED", "service identity required", False))
        if path == "/v1/jobs":
            if body.get("project_id") and body["project_id"] != project:
                return Resp(403, self.r._err(body.get("request_id", "na"), "FORBIDDEN", "project binding mismatch", False))
            extra = any(k not in {"project_id", "operation", "idempotency_key", "request_id", "data_class", "payload", "budget"} for k in body)
            code, data = self.r.submit_job(
                project_id=project,
                operation=body.get("operation", ""),
                idempotency_key=headers.get("idempotency-key") or body.get("idempotency_key", ""),
                request_id=headers.get("x-request-id") or body.get("request_id", "req-1"),
                data_class=body.get("data_class", "TEST_ONLY"),
                payload=body.get("payload") or {},
                budget=body.get("budget"),
                extra_fields=extra,
            )
            return Resp(code, data)
        if path.startswith("/v1/jobs/") and path.endswith("/cancel"):
            job_id = path.split("/")[3]
            return Resp(*self.r.cancel(job_id, project))
        if path == "/v1/leases/claim":
            code, data = self.r.claim(project_id=project, worker_id=body.get("worker_id", "w1"), request_id="c")
            return Resp(code, data)
        if "/heartbeat" in path:
            lease_id = path.split("/")[3]
            return Resp(*self.r.heartbeat(lease_id, project, body.get("worker_id", "w1")))
        if "/complete" in path:
            lease_id = path.split("/")[3]
            return Resp(*self.r.complete(
                lease_id, project, body.get("worker_id", "w1"),
                success=body.get("success", True),
                retryable=body.get("retryable", False),
                error_code=body.get("error_code"),
                artifact=body.get("artifact"),
                unknown=body.get("unknown", False),
            ))
        if path == "/v1/reconcile":
            return Resp(*self.r.reconcile(body.get("job_id", ""), project))
        if path.startswith("/v1/modules/") and path.endswith("/schedule"):
            module = path.split("/")[3]
            return Resp(*self.r.block_module_schedule(module))
        if path == "/v1/production/deny":
            return Resp(*self.r.deny_production())
        if path == "/v1/capabilities":
            from app import CODE_COMMIT, CONTRACT_SHA256, CONTRACT_VERSION
            return Resp(200, {
                "contract_version": CONTRACT_VERSION,
                "service": "content-workflow",
                "code_commit": CODE_COMMIT,
                "contract_sha256": CONTRACT_SHA256,
                "mode": "MOCK",
                "enabled_operations": ["plan", "draft", "evidence", "approve", "publish"],
                "max_json_bytes": 2097152,
            })
        return Resp(404, {"error": "not found"})

    def get(self, path: str, headers=None):
        headers = {k.lower(): v for k, v in (headers or {}).items()}
        project = headers.get("x-project-id")
        svc = headers.get("x-service-id")
        if path == "/healthz":
            return Resp(200, {"status": "ok"})
        if path == "/v1/capabilities":
            if not svc or not project:
                return Resp(401, self.r._err("na", "UNAUTHORIZED", "service identity required", False))
            return self.post(path, headers=headers, json={})
        if path.startswith("/v1/jobs/"):
            job_id = path.split("/")[3]
            return Resp(*self.r.get_job(job_id, project))
        return Resp(404, {})
