from __future__ import annotations

import json
import os
from pathlib import Path

from .notion_transport import HttpTransport, TransportError

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MANIFEST = ROOT / "docs" / "STAGING_ACCESS_MANIFEST.json"
NOTION_VERSION = "2025-09-03"
MAX_PAGES = 50
MAX_RELATION_PAGES = 20


def load_manifest(path: Path) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def classify(err: TransportError) -> str:
    if err.code in {
        "OUTSIDE_ALLOWLIST",
        "SCHEMA_DRIFT",
        "MISSING_PARENT",
        "MALFORMED_RESPONSE",
        "CURSOR_LOOP",
        "TARGET_INACCESSIBLE",
        "RELATION_UNVERIFIED",
        "EMPTY_NOT_PROOF",
        "RELATION_TARGET_MISMATCH",
        "RELATION_TRUNCATED",
        "BLOCKED_OWNER_INPUT",
        "BUDGET_EXCEEDED",
    }:
        return err.code
    if err.status == 404:
        return "TARGET_INACCESSIBLE"
    if err.status == 429:
        return "RATE_LIMITED"
    if err.status in (401, 403):
        return "AUTH_DENIED"
    if err.code == "TIMEOUT_OR_NETWORK":
        return "TIMEOUT_OR_NETWORK"
    return err.code


def _parent_ds(obj: dict | None) -> str | None:
    parent = (obj or {}).get("parent") or {}
    return parent.get("data_source_id") or parent.get("database_id")



def _collect_relation_items(obj: dict) -> list[dict]:
    items: list[dict] = []
    if not isinstance(obj, dict):
        return items
    rel = obj.get("relation")
    if isinstance(rel, list):
        items.extend(x for x in rel if isinstance(x, dict))
    elif isinstance(rel, dict) and rel.get("id"):
        items.append(rel)
    for r in obj.get("results") or []:
        if not isinstance(r, dict):
            continue
        if "relation" in r and isinstance(r["relation"], dict) and r["relation"].get("id"):
            items.append({"id": r["relation"]["id"]})
        elif r.get("object") == "page" and r.get("id"):
            items.append({"id": r["id"]})
        elif r.get("id") and isinstance(r.get("relation"), list):
            items.extend(x for x in r["relation"] if isinstance(x, dict) and x.get("id"))
    return items



def resolve_expected_snapshot(manifest: dict, ds: str) -> dict | None:
    block = manifest.get("expected_schema")
    if not block:
        ref = manifest.get("expected_schema_path")
        if ref:
            path = Path(ref)
            if not path.is_file():
                path = ROOT / ref
            if path.is_file():
                block = json.loads(path.read_text(encoding="utf-8"))
    if not block:
        return None
    if "by_data_source" in block and isinstance(block["by_data_source"], dict):
        return block["by_data_source"].get(ds)
    if ds in block and isinstance(block[ds], dict) and "properties" in block[ds]:
        return block[ds]
    return None


def compare_schema_to_expected(observed: dict, expected: dict, ds: str) -> None:
    if expected.get("id") and expected.get("id") != observed.get("id", ds) and expected.get("id") != ds:
        raise TransportError("SCHEMA_DRIFT", None, "expected schema id mismatch")
    exp_props = expected.get("properties") or {}
    obs_props = observed.get("properties") or {}
    if not exp_props:
        raise TransportError("BLOCKED_OWNER_INPUT", None, "expected snapshot has no properties")
    for name, espec in exp_props.items():
        if name not in obs_props:
            raise TransportError("SCHEMA_DRIFT", None, f"missing property {name}")
        ospec = obs_props[name]
        if not isinstance(ospec, dict) or not isinstance(espec, dict):
            raise TransportError("MALFORMED_RESPONSE", None, name)
        if espec.get("id") and ospec.get("id") and espec.get("id") != ospec.get("id"):
            raise TransportError("SCHEMA_DRIFT", None, f"property id drift {name}")
        if espec.get("type") and ospec.get("type") != espec.get("type"):
            raise TransportError("SCHEMA_DRIFT", None, f"property type drift {name}")
        if espec.get("type") == "relation":
            exp_dest = (espec.get("relation") or {}).get("data_source_id")
            obs_dest = (ospec.get("relation") or {}).get("data_source_id")
            if exp_dest and obs_dest and exp_dest != obs_dest:
                raise TransportError("SCHEMA_DRIFT", None, f"relation dest {name}: observed {obs_dest} expected {exp_dest}")


def run_preflight(
    manifest_path: str | Path | None = None,
    read_only: bool = True,
    transport=None,
    live: bool | None = None,
) -> dict:
    manifest = load_manifest(manifest_path or DEFAULT_MANIFEST)
    token = os.getenv("STAGING_NOTION_TOKEN", "").strip()
    enabled = os.getenv("STAGING_ENABLED", "").lower() in {"1", "true", "yes"}
    if live is None:
        live = enabled and bool(token) and transport is None

    allow = {db["data_source_id"] for db in manifest.get("databases", [])}
    report = {
        "status": "NOT_RUN",
        "mode": "LIVE_READ" if live else "MOCK",
        "notion_version": NOTION_VERSION,
        "reason": None,
        "test_run_id": os.getenv("TEST_RUN_ID"),
        "read_only": bool(read_only),
        "writes_attempted": 0,
        "production_writes": 0,
        "requests_attempted": 0,
        "databases": [],
        "errors": [],
        "relation_targets": [],
        "data_class": "TEST_ONLY",
    }

    if live and not token:
        report["status"] = "BLOCKED_ACCESS"
        report["reason"] = "STAGING_NOTION_TOKEN absent"
        return report
    if token and not enabled and transport is None:
        report["status"] = "BLOCKED_OPT_IN"
        report["reason"] = "token present but STAGING_ENABLED is not true"
        return report

    if transport is None:
        if live:
            transport = HttpTransport()
        else:
            report["status"] = "IMPLEMENTED_MOCK_READY"
            report["reason"] = "network off; inject transport to execute protocol"
            for db in manifest.get("databases", []):
                report["databases"].append(
                    {
                        "name": db["name"],
                        "data_source_id": db["data_source_id"],
                        "relation_parent_verified": False,
                        "relation_targets_verified": False,
                        "rows_seen": 0,
                    }
                )
            return report

    headers = {
        "Authorization": f"Bearer {token or 'mock'}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type": "application/json",
    }

    def call(method: str, url: str, body: bytes | None = None) -> dict:
        report["requests_attempted"] += 1
        return transport.request(method, url, headers, body)

    for db in manifest.get("databases", []):
        ds = db["data_source_id"]
        entry = {
            "name": db["name"],
            "data_source_id": ds,
            "relation_parent_verified": False,
            "relation_targets_verified": False,
            "schema_ok": False,
            "rows_seen": 0,
            "pages": 0,
            "http_status": [],
            "targets": [],
            "scope": "UNKNOWN",
        }
        try:
            schema = call("GET", f"https://api.notion.com/v1/data_sources/{ds}")
            entry["http_status"].append(schema.get("status"))
            sbody = schema.get("body") or {}
            if not isinstance(sbody, dict) or "properties" not in sbody:
                raise TransportError("MALFORMED_RESPONSE", None, "schema missing properties")
            if sbody.get("id") and sbody.get("id") != ds:
                raise TransportError("SCHEMA_DRIFT", None, "schema id mismatch")
            expected_snap = resolve_expected_snapshot(manifest, ds)
            if expected_snap is None:
                raise TransportError("BLOCKED_OWNER_INPUT", None, "no trusted expected_schema pin")
            compare_schema_to_expected(sbody, expected_snap, ds)
            entry["schema_ok"] = True
            entry["schema_pin"] = "expected_schema"
            schema_props = sbody.get("properties") or {}
            relation_specs = {
                name: spec
                for name, spec in schema_props.items()
                if isinstance(spec, dict) and spec.get("type") == "relation"
            }
            relation_props = list(relation_specs)
            expected_target = {}
            exp_props = expected_snap.get("properties") or {}
            for name, espec in exp_props.items():
                if isinstance(espec, dict) and espec.get("type") == "relation":
                    dest = (espec.get("relation") or {}).get("data_source_id")
                    if dest:
                        expected_target[name] = dest
                        expected_target[espec.get("id") or name] = dest
            # never take destination from provider response as trusted mapping
            if not expected_target:
                entry["note"] = "expected snapshot has no relation destinations; cannot verify mappings"
            entry["property_coverage"] = {n: {"expected_ds": expected_target.get(n), "verified": False} for n in expected_target if n in exp_props}

            cursor = None
            seen_cursors: set[str] = set()
            rows: list = []
            for _ in range(MAX_PAGES):
                if cursor is not None and cursor in seen_cursors:
                    raise TransportError("CURSOR_LOOP", None, "repeated cursor")
                if cursor:
                    seen_cursors.add(cursor)
                resp = call(
                    "POST",
                    f"https://api.notion.com/v1/data_sources/{ds}/query",
                    json.dumps({"start_cursor": cursor} if cursor else {}).encode(),
                )
                entry["http_status"].append(resp.get("status"))
                body = resp.get("body")
                if not isinstance(body, dict) or "results" not in body:
                    raise TransportError("MALFORMED_RESPONSE", None, "query body")
                batch = body.get("results") or []
                if not isinstance(batch, list):
                    raise TransportError("MALFORMED_RESPONSE", None, "results not list")
                rows.extend(batch)
                entry["pages"] += 1
                if body.get("has_more"):
                    nxt = body.get("next_cursor")
                    if not nxt:
                        raise TransportError("MALFORMED_RESPONSE", None, "has_more without cursor")
                    cursor = nxt
                    continue
                break
            else:
                raise TransportError("CURSOR_LOOP", None, "page budget exceeded")

            entry["rows_seen"] = len(rows)
            if not rows:
                entry["scope"] = "NOT_APPLICABLE"
                entry["note"] = "empty result does not prove relation targets"
                report["databases"].append(entry)
                continue

            saw_relation = False
            for row in rows:
                parent = _parent_ds(row)
                if not parent:
                    raise TransportError("MISSING_PARENT", None, str(row.get("id") or "row"))
                if parent != ds:
                    raise TransportError("OUTSIDE_ALLOWLIST", 403, parent)
                entry["relation_parent_verified"] = True
                props = row.get("properties") or {}
                names = relation_props or [
                    k for k, v in props.items() if isinstance(v, dict) and v.get("type") == "relation"
                ]
                for pname in names:
                    rel = props.get(pname) or {}
                    spec = relation_specs.get(pname) or {}
                    if not isinstance(rel, dict) or rel.get("type") != "relation":
                        if pname in relation_specs:
                            raise TransportError("MALFORMED_RESPONSE", None, f"missing relation property {pname}")
                        continue
                    saw_relation = True
                    expected_ds = expected_target.get(pname) or expected_target.get(rel.get("id") or "") or (spec.get("relation") or {}).get("data_source_id")
                    if not expected_ds:
                        raise TransportError("BLOCKED_OWNER_INPUT", None, f"no expected target DS for {pname}")
                    items = _collect_relation_items(rel)
                    prop_id = rel.get("id") or spec.get("id") or pname
                    from urllib.parse import quote
                    rel_cursor = rel.get("next_cursor")
                    if rel.get("has_more") and not rel_cursor:
                        raise TransportError("RELATION_TRUNCATED", None, pname)
                    need_pages = bool(rel.get("has_more"))
                    hops = 0
                    seen_rel = set()
                    while need_pages and hops < MAX_RELATION_PAGES:
                        hops += 1
                        q = f"https://api.notion.com/v1/pages/{row.get('id')}/properties/{quote(str(prop_id), safe='')}"
                        if rel_cursor:
                            if rel_cursor in seen_rel:
                                raise TransportError("CURSOR_LOOP", None, "relation cursor loop")
                            seen_rel.add(rel_cursor)
                            q += f"?start_cursor={quote(rel_cursor)}"
                        more = call("GET", q)
                        mbody = more.get("body") or {}
                        extra = _collect_relation_items(mbody)
                        if not extra and rel.get("has_more") and hops == 1 and not rel_cursor:
                            raise TransportError("RELATION_TRUNCATED", None, pname)
                        items.extend(extra)
                        if mbody.get("has_more"):
                            rel_cursor = mbody.get("next_cursor")
                            if not rel_cursor:
                                raise TransportError("RELATION_TRUNCATED", None, "has_more without property cursor")
                            need_pages = True
                            continue
                        need_pages = False
                        break
                    else:
                        if need_pages:
                            raise TransportError("BUDGET_EXCEEDED", None, pname)
                    if rel.get("has_more") and hops == 0:
                        raise TransportError("RELATION_TRUNCATED", None, pname)
                    if not items:
                        raise TransportError("RELATION_UNVERIFIED", None, pname)
                    for item in items:
                        tid = item.get("id") if isinstance(item, dict) else None
                        if not tid:
                            raise TransportError("MALFORMED_RESPONSE", None, "relation item")
                        page = call("GET", f"https://api.notion.com/v1/pages/{tid}")
                        pbody = page.get("body") or {}
                        tparent = _parent_ds(pbody)
                        rec = {
                            "target_id_redacted": tid[:8] + "…",
                            "parent_ds": tparent,
                            "expected_ds": expected_ds,
                            "property": pname,
                            "ok": False,
                        }
                        if not tparent:
                            raise TransportError("MISSING_PARENT", None, tid)
                        if tparent not in allow:
                            raise TransportError("OUTSIDE_ALLOWLIST", 403, tparent)
                        if tparent != expected_ds:
                            raise TransportError("RELATION_TARGET_MISMATCH", None, f"{pname}:{tparent}!={expected_ds}")
                        rec["ok"] = True
                        entry["targets"].append(rec)
                        report["relation_targets"].append(rec)
                        if "property_coverage" in entry and pname in entry["property_coverage"]:
                            entry["property_coverage"][pname]["verified"] = True
            if saw_relation and entry["targets"] and all(t.get("ok") for t in entry["targets"]):
                entry["relation_targets_verified"] = True
                entry["scope"] = "VERIFIED"
            elif not saw_relation:
                entry["scope"] = "UNKNOWN"
                entry["note"] = "no relation properties observed; targets not proven"
            else:
                entry["scope"] = "UNKNOWN"
        except TransportError as e:
            kind = classify(e)
            entry["error"] = kind
            entry["relation_targets_verified"] = False
            if kind in {"MISSING_PARENT", "OUTSIDE_ALLOWLIST", "MALFORMED_RESPONSE"}:
                if kind != "OUTSIDE_ALLOWLIST" or not entry["relation_parent_verified"]:
                    pass
            report["errors"].append({"database": db["name"], "class": kind, "status": e.status})
        report["databases"].append(entry)

    if report["errors"]:
        classes = {e["class"] for e in report["errors"]}
        if "OUTSIDE_ALLOWLIST" in classes or "RELATION_TARGET_MISMATCH" in classes:
            report["status"] = "BLOCKED_STAGING_RELATIONS"
        elif "BLOCKED_OWNER_INPUT" in classes:
            report["status"] = "BLOCKED_OWNER_INPUT"
        elif "RELATION_TRUNCATED" in classes or "BUDGET_EXCEEDED" in classes:
            report["status"] = "CHANGES_REQUIRED"
        elif "AUTH_DENIED" in classes:
            report["status"] = "BLOCKED_ACCESS"
        elif "RATE_LIMITED" in classes:
            report["status"] = "RATE_LIMITED"
        elif "TIMEOUT_OR_NETWORK" in classes:
            report["status"] = "TIMEOUT_OR_NETWORK"
        else:
            report["status"] = "CHANGES_REQUIRED"
        report["reason"] = ",".join(sorted(classes))
    else:
        verified = all(d.get("relation_targets_verified") for d in report["databases"])
        if verified and report["databases"]:
            report["status"] = "PREFLIGHT_OK" if live else "PREFLIGHT_MOCK_OK"
        else:
            report["status"] = "PREFLIGHT_INCOMPLETE"
            report["reason"] = "not every DS has verified relation targets"
    return report
