"""V6 actual-process TEST_ONLY harness for the integrated candidate."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[3]
REPO = ROOT.parent
DATA = Path(os.environ.get("THBISON_LAB_DATA", ROOT / ".lab-data")).resolve()
EVIDENCE = Path(os.environ.get("THBISON_EVIDENCE_DIR", ROOT / "evidence-current")).resolve()
PROCS: list[subprocess.Popen] = []


def call(method: str, url: str, body=None, headers=None, expected=(200,)):
    raw = None if body is None else json.dumps(body).encode()
    req = Request(url, data=raw, method=method, headers={"Content-Type": "application/json", **(headers or {})})
    try:
        with urlopen(req, timeout=8) as response:
            status, payload = response.status, json.loads(response.read() or b"{}")
    except HTTPError as exc:
        status, payload = exc.code, json.loads(exc.read() or b"{}")
    if status not in expected:
        raise RuntimeError(f"HTTP_{status}:{url}:{payload}")
    return status, payload


def wait_health(port: int, proc: subprocess.Popen):
    for _ in range(100):
        if proc.poll() is not None:
            raise RuntimeError(f"PROCESS_EXITED_BEFORE_HEALTH:{port}:{proc.returncode}")
        try:
            call("GET", f"http://127.0.0.1:{port}/healthz")
            return
        except Exception:
            time.sleep(0.05)
    raise RuntimeError(f"HEALTH_TIMEOUT:{port}")


def start(command: list[str], *, cwd: Path, env: dict[str, str], port: int) -> subprocess.Popen:
    log = open(EVIDENCE / f"process-{port}.log", "wb")
    proc = subprocess.Popen(command, cwd=cwd, env={**os.environ, **env}, stdout=log, stderr=subprocess.STDOUT)
    proc._thbison_log = log  # type: ignore[attr-defined]
    PROCS.append(proc)
    wait_health(port, proc)
    return proc


def stop(proc: subprocess.Popen):
    if proc.poll() is None:
        proc.terminate()
        try:
            proc.wait(5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(5)
    getattr(proc, "_thbison_log", None).close()
    if proc in PROCS:
        PROCS.remove(proc)


def main() -> int:
    if DATA.exists():
        shutil.rmtree(DATA)
    if EVIDENCE.exists():
        shutil.rmtree(EVIDENCE)
    DATA.mkdir(parents=True)
    EVIDENCE.mkdir(parents=True)
    node_hook = (ROOT / "modules/vendor2/tests/register-ts-ext.mjs").as_uri()
    py_path = os.pathsep.join([str(REPO / "src"), os.environ.get("PYTHONPATH", "")])
    common = {"ALLOW_PRODUCTION": "false", "ALLOW_PUBLIC_EFFECTS": "false", "APP_MODE": "MOCK"}
    try:
        start(["node", "--experimental-strip-types", "--import", str(node_hook), str(ROOT / "integration/services/planning-server.mjs")], cwd=ROOT, env={**common, "PORT": "18081", "THBISON_DATA_DIR": str(DATA / "v1")}, port=18081)
        start(["node", "--experimental-strip-types", "--import", str(node_hook), str(ROOT / "integration/services/writer-server.mjs")], cwd=ROOT, env={**common, "PORT": "18082"}, port=18082)
        runtime = start([sys.executable, str(ROOT / "integration/services/runtime-server.py")], cwd=ROOT, env={**common, "PORT": "18083", "RUNTIME_DB": str(DATA / "runtime.sqlite")}, port=18083)
        start([sys.executable, str(ROOT / "integration/services/knowledge-gateway-server.py")], cwd=REPO, env={**common, "PORT": "18084", "PYTHONPATH": py_path, "KNOWLEDGE_FIXTURE": str(REPO / "fixtures/integration/knowledge-output.test-only.json")}, port=18084)

        planning_headers = {"Authorization": "Bearer thbison-test-token-aaaaaaaa", "X-Contract-Version": "1.0.0", "Idempotency-Key": "integration-planning-001"}
        request = json.loads((ROOT / "modules/vendor1/vendor_kit/contracts/examples/ResearchRequest.json").read_text(encoding="utf-8"))
        request["budget"]["deadline_at"] = "2030-01-01T00:05:00Z"
        request["seeds"] = ["pa lang xich keo tay"]
        request["existing_pages"] = []
        _, admitted = call("POST", "http://127.0.0.1:18081/v1/planning/jobs", request, planning_headers, (202,))
        output = None
        for _ in range(100):
            _, state = call("GET", f"http://127.0.0.1:18081/v1/planning/jobs/{admitted['job_id']}", headers=planning_headers)
            if state["status"] == "SUCCEEDED":
                _, output = call("GET", f"http://127.0.0.1:18081/v1/planning/jobs/{admitted['job_id']}/output", headers=planning_headers)
                break
            time.sleep(0.02)
        if output is None:
            raise RuntimeError("PLANNER_TIMEOUT")

        _, bundle = call("POST", "http://127.0.0.1:18084/v1/knowledge/query", {"project_id": output["brief"]["project_id"]}, {"Authorization": "Bearer lab-knowledge-token", "X-Contract-Version": "1.0.0", "Idempotency-Key": "integration-knowledge-001"})
        writer_headers = {"Authorization": "Bearer lab-writer-token", "X-Contract-Version": "1.0.0"}
        _, article = call("POST", "http://127.0.0.1:18082/v1/draft", {"brief": output["brief"], "bundle": bundle}, writer_headers)
        _, approval = call("POST", "http://127.0.0.1:18082/v1/approve", {"article_id": article["article_id"], "article_revision": article["article_revision"], "destination_id": "test-cms"}, writer_headers)

        authority = DATA / "cms-authority.json"
        authority.write_text(json.dumps({"article": article, "approval": approval, "evidence": bundle}), encoding="utf-8")
        cms = start([sys.executable, "-m", "app.httpapi"], cwd=ROOT / "modules/vendor5", env={**common, "PORT": "18085", "CMS_LEDGER_PATH": str(DATA / "cms.sqlite"), "CMS_AUTHORITY_FIXTURE": str(authority)}, port=18085)

        runtime_headers = {"X-Service-Id": "v6-lab", "X-Project-Id": "test-thbison", "X-Contract-Version": "1.0.0"}
        job_body = {"operation": "publish", "idempotency_key": f"publish-{article['article_id']}", "request_id": "runtime-publish-001", "data_class": "TEST_ONLY", "payload": {"article_id": article["article_id"], "article_revision": article["article_revision"]}}
        _, job = call("POST", "http://127.0.0.1:18083/v1/jobs", job_body, runtime_headers, (202,))
        _, lease = call("POST", "http://127.0.0.1:18083/v1/leases/claim", {"worker_id": "v6-worker", "request_id": "claim-request"}, runtime_headers)
        publish = {"contract_version": "1.0.0", "project_id": "test-thbison", "data_class": "TEST_ONLY", "request_id": "cms-dry-run-001", "article_id": article["article_id"], "article_revision": article["article_revision"], "content_sha256": article["content_sha256"], "evidence_snapshot_sha256": bundle["snapshot_sha256"], "approval_id": approval["approval_id"], "destination_id": "test-cms", "mode": "DRY_RUN", "scheduled_at": None}
        cms_headers = {"Authorization": "Bearer test-service", "X-Contract-Version": "1.0.0", "Idempotency-Key": "cms-dry-run-integration-001", "X-Test-Run-Id": "thbison-integration-01"}
        _, receipt = call("POST", "http://127.0.0.1:18085/v1/publications", publish, cms_headers, (202,))
        _, completed = call("POST", f"http://127.0.0.1:18083/v1/leases/{lease['lease_id']}/complete", {"worker_id": "v6-worker", "success": True, "artifact": receipt}, runtime_headers)

        # Retry owner is V3. Idempotent CMS and V3 requests must not duplicate effects.
        _, receipt_retry = call("POST", "http://127.0.0.1:18085/v1/publications", publish, cms_headers, (202,))
        _, job_retry = call("POST", "http://127.0.0.1:18083/v1/jobs", job_body, runtime_headers, (202,))
        if receipt_retry != receipt or job_retry["job_id"] != job["job_id"]:
            raise RuntimeError("DUPLICATE_EFFECT_OR_JOB")

        stop(runtime)
        runtime = start([sys.executable, str(ROOT / "integration/services/runtime-server.py")], cwd=ROOT, env={**common, "PORT": "18083", "RUNTIME_DB": str(DATA / "runtime.sqlite")}, port=18083)
        _, readback = call("GET", f"http://127.0.0.1:18083/v1/jobs/{job['job_id']}", headers=runtime_headers)
        if readback["status"] != "SUCCEEDED":
            raise RuntimeError(f"RESTART_READBACK_FAILED:{readback}")

        report = {
            "verdict": "ACTUAL_PROCESS_SYNTHETIC_PASS",
            "data_class": "TEST_ONLY",
            "live_data_pass": False,
            "notion_status": "NOTION_TARGET_MISSING",
            "public_effects": 0,
            "processes": {"v1": "actual-source", "v2": "actual-source", "v3": "actual-source", "v4_gateway": "actual-source", "v5": "actual-source", "v6": "actual-harness"},
            "identity": {"project_id": article["project_id"], "brief_id": article["brief_id"], "brief_revision": article["brief_revision"], "article_id": article["article_id"], "article_revision": article["article_revision"], "evidence_snapshot_sha256": article["evidence_snapshot_sha256"], "approval_id": approval["approval_id"]},
            "runtime": {"job_id": job["job_id"], "status": completed["status"], "restart_readback": readback["status"], "single_retry_owner": "vendor3"},
            "cms": {"mode": "DRY_RUN", "receipt": receipt, "idempotent_retry": True},
        }
        (EVIDENCE / "actual-process-report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        for name, value in (("planning", output), ("brief", output["brief"]), ("evidence", bundle), ("article", article), ("approval", approval), ("runtime", completed), ("cms", receipt)):
            (EVIDENCE / f"{name}.json").write_text(json.dumps(value, indent=2, ensure_ascii=False), encoding="utf-8")
        print(json.dumps(report, indent=2))
        return 0
    finally:
        for proc in list(reversed(PROCS)):
            stop(proc)


if __name__ == "__main__":
    raise SystemExit(main())
