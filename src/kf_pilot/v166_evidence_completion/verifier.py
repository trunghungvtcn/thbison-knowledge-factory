"""Independent committed-run verifier; intentionally does not import the producer."""
import json
from pathlib import Path

from .canonical import bytes_for, load, require, sha256


def verify(inputs, committed_run, report):
    run = Path(committed_run)
    marker = load(run / "COMMIT_MARKER.json")
    require(marker == {"schema_version": 1, "state": "COMMITTED", "artifact_hashes_sha256": marker["artifact_hashes_sha256"], "run_config_sha256": marker["run_config_sha256"]}, "COMMIT_MARKER_SCHEMA")
    hashes = load(run / "artifact_hashes.json")
    require(marker["artifact_hashes_sha256"] == sha256((run / "artifact_hashes.json").read_bytes()), "COMMIT_MARKER_HASH")
    expected = set(hashes) | {"artifact_hashes.json", "COMMIT_MARKER.json"}
    require({p.name for p in run.iterdir() if p.is_file()} == expected, "COMMITTED_FILESET_MISMATCH")
    for name, expected_hash in hashes.items():
        require(Path(name).name == name and sha256((run / name).read_bytes()) == expected_hash, "COMMITTED_HASH_MISMATCH", name)
    config_path = Path(inputs)
    require(marker["run_config_sha256"] == sha256(config_path.read_bytes()), "INPUT_BINDING_MISMATCH")
    readiness = load(run / "readiness.json")
    require(readiness["authorized_to_execute"] is False and readiness["apply_status"] in {"NOT_EXECUTED", "LOCAL_SHADOW_PROJECTED"}, "UNAUTHORIZED_PROJECTION")
    ledger = load(run / "projected_ledger.json")["issues"]
    require(len(ledger) == 85 and len({x["issue_id"] for x in ledger}) == 85, "LEDGER_UNIVERSE_MISMATCH")
    require(load(run / "canary_plan.json") == {"records": [], "authorized_to_execute": False}, "CANARY_NOT_EMPTY")
    projected = load(run / "projected_records.json")
    events = []
    raw_events = (run / "ledger_events.jsonl").read_text(encoding="utf-8")
    decoder, index = json.JSONDecoder(), 0
    while index < len(raw_events):
        while index < len(raw_events) and raw_events[index].isspace(): index += 1
        if index < len(raw_events):
            value, index = decoder.raw_decode(raw_events, index); events.append(value)
    if readiness["apply_status"] == "NOT_EXECUTED":
        require(projected == {"records": [], "operation": "NO_CHANGE"} and not events, "WAITING_RUN_HAS_DELTAS")
    else:
        require(projected["operation"] == "LOCAL_SHADOW_UPDATE" and projected["records"] and events, "PROJECTED_RUN_EMPTY")
        require(len({x["issue_id"] for x in events}) == len(events), "DUPLICATE_RESOLUTION_EVENT")
        by_issue = {x["issue_id"]: x for x in ledger}
        for event in events:
            require(by_issue[event["issue_id"]]["resolution_status"] == "RESOLVED" and by_issue[event["issue_id"]]["resolution_event"] == event, "RESOLUTION_EVENT_MISMATCH")
        for record in projected["records"]:
            require(record["operation"] == "LOCAL_SHADOW_UPDATE" and record["decision"] not in {"HOLD", "REJECTED"}, "TARGET_OR_HUMAN_STATE_INVALID")
    result = {"status": "V166_INDEPENDENT_VERIFY_PASS", "committed": True, "ledger_issues": 85,
              "production_writes": 0, "human_field_writes": 0, "authorized_to_execute": False}
    report = Path(report)
    require(not report.exists(), "REPORT_ALREADY_EXISTS")
    report.write_bytes(bytes_for(result) + b"\n")
    return result
