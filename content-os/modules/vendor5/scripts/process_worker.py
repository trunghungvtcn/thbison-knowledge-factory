#!/usr/bin/env python3
"""OS-process worker for CMS-17: publish one staging draft then print receipt JSON."""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.adapter import CmsAdapter
from app.fixtures import install_staging, load_demo_authority


def stats() -> int:
    ledger = os.environ["CMS_LEDGER_PATH"]
    ad = CmsAdapter(ledger)
    sys.stdout.write(json.dumps({"side_effects": ad.sim.side_effects, "create_calls": ad.sim.create_calls}))
    sys.stdout.write("\n")
    return 0


def main() -> int:
    if len(sys.argv) > 1 and sys.argv[1] == "stats":
        return stats()

    ledger = os.environ["CMS_LEDGER_PATH"]
    ad = CmsAdapter(ledger)
    load_demo_authority(ad.authority)
    art, appr, ev = install_staging(ad.authority)
    req = {
        "contract_version": "1.0.0",
        "project_id": "test-thbison",
        "data_class": "STAGING",
        "request_id": "proc-publish-1",
        "article_id": art["article_id"],
        "article_revision": art["article_revision"],
        "content_sha256": art["content_sha256"],
        "evidence_snapshot_sha256": ev["snapshot_sha256"],
        "approval_id": appr["approval_id"],
        "destination_id": appr["destination_id"],
        "mode": "STAGING_DRAFT",
        "scheduled_at": None,
    }
    rec = ad.publish(req, "process-worker-id01", "Bearer test-service", test_run_id="run-process")
    public = {k: v for k, v in rec.items() if not k.startswith("_")}
    sys.stdout.write(json.dumps(public, ensure_ascii=True, separators=(",", ":")))
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
