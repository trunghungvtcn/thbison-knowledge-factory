"""Four worker simulators driven only by the runtime scheduler."""
from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


@dataclass
class SimConfig:
    delay_s: float = 0.0
    timeout: bool = False
    rate_limit: bool = False
    duplicate: bool = False
    crash: bool = False
    unknown: bool = False
    fail_retryable: bool = False
    fail_permanent: bool = False


class WorkerSim:
    name: str = "base"

    def __init__(self, cfg: SimConfig | None = None) -> None:
        self.cfg = cfg or SimConfig()
        self.calls = 0

    def run(self, lease: dict[str, Any]) -> dict[str, Any]:
        self.calls += 1
        if self.cfg.delay_s:
            time.sleep(self.cfg.delay_s)
        if self.cfg.crash:
            raise RuntimeError("simulated crash")
        if self.cfg.timeout:
            return {"success": False, "retryable": True, "error_code": "TIMEOUT", "unknown": False}
        if self.cfg.rate_limit:
            return {"success": False, "retryable": True, "error_code": "RATE_LIMITED"}
        if self.cfg.unknown:
            return {"success": False, "unknown": True}
        if self.cfg.fail_permanent:
            return {"success": False, "retryable": False, "error_code": "VALIDATION_ERROR"}
        if self.cfg.fail_retryable:
            return {"success": False, "retryable": True, "error_code": "PROVIDER_ERROR"}
        artifact = {
            "artifact_id": f"art-{self.name}-{lease.get('job_id','x')}"[:80],
            "sha256": "e" * 64,
            "bytes": 12,
            "media_type": "application/json",
        }
        return {"success": True, "artifact": artifact, "duplicate": self.cfg.duplicate}


class SeoPlanningSim(WorkerSim):
    name = "seo-planning"


class ContentWorkflowSim(WorkerSim):
    name = "content-workflow"


class KnowledgeGatewaySim(WorkerSim):
    name = "knowledge-gateway"


class AssetGatewaySim(WorkerSim):
    name = "asset-gateway"


PIPELINE = ["plan", "evidence", "draft", "approve", "publish"]
OP_WORKER = {
    "plan": SeoPlanningSim,
    "evidence": KnowledgeGatewaySim,
    "draft": ContentWorkflowSim,
    "approve": ContentWorkflowSim,
    "publish": AssetGatewaySim,
}
