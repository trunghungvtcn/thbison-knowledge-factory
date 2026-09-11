"""Start or stop the localhost-only TEST_ONLY integration lab."""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTENT = ROOT / "content-os"
STATE_DIR = CONTENT / ".lab-control"
STATE = STATE_DIR / "pids.json"


def commands():
    py_path = os.pathsep.join((str(ROOT / "src"), os.environ.get("PYTHONPATH", "")))
    return [
        (18081, ["node", "--experimental-strip-types", "--import", (CONTENT / "modules/vendor2/tests/register-ts-ext.mjs").as_uri(), str(CONTENT / "integration/services/planning-server.mjs")], CONTENT, {"THBISON_DATA_DIR": str(STATE_DIR / "v1")}),
        (18082, ["node", "--experimental-strip-types", "--import", (CONTENT / "modules/vendor2/tests/register-ts-ext.mjs").as_uri(), str(CONTENT / "integration/services/writer-server.mjs")], CONTENT, {}),
        (18083, [sys.executable, str(CONTENT / "integration/services/runtime-server.py")], CONTENT, {"RUNTIME_DB": str(STATE_DIR / "runtime.sqlite")}),
        (18084, [sys.executable, str(CONTENT / "integration/services/knowledge-gateway-server.py")], ROOT, {"PYTHONPATH": py_path, "KNOWLEDGE_FIXTURE": str(ROOT / "fixtures/integration/knowledge-output.test-only.json")}),
        (18085, [sys.executable, "-m", "app.httpapi"], CONTENT / "modules/vendor5", {"CMS_LEDGER_PATH": str(STATE_DIR / "cms.sqlite")}),
    ]


def up() -> int:
    if STATE.exists():
        raise SystemExit("LAB_ALREADY_STARTED; run labctl.py down first")
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    records = []
    try:
        for port, command, cwd, extra in commands():
            log = open(STATE_DIR / f"process-{port}.log", "ab")
            env = {**os.environ, "PORT": str(port), "APP_MODE": "MOCK", "ALLOW_PRODUCTION": "false", "ALLOW_PUBLIC_EFFECTS": "false", **extra}
            flags = subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            proc = subprocess.Popen(command, cwd=cwd, env=env, stdout=log, stderr=subprocess.STDOUT, creationflags=flags, start_new_session=os.name != "nt")
            records.append({"pid": proc.pid, "port": port})
        STATE.write_text(json.dumps(records, indent=2), encoding="utf-8")
        print("LAB_UP localhost ports 18081..18085; TEST_ONLY; public effects disabled")
        return 0
    except Exception:
        STATE.write_text(json.dumps(records), encoding="utf-8")
        down()
        raise


def down() -> int:
    if not STATE.exists():
        print("LAB_ALREADY_DOWN")
        return 0
    records = json.loads(STATE.read_text(encoding="utf-8"))
    for rec in reversed(records):
        try:
            if os.name == "nt":
                subprocess.run(["taskkill", "/PID", str(rec["pid"]), "/T", "/F"], check=False, capture_output=True)
            else:
                os.killpg(rec["pid"], signal.SIGTERM)
        except (ProcessLookupError, PermissionError):
            pass
    STATE.unlink()
    print("LAB_DOWN")
    return 0


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else ""
    if action == "up":
        raise SystemExit(up())
    if action == "down":
        raise SystemExit(down())
    raise SystemExit("usage: python scripts/labctl.py up|down")
