"""Read-only staging preflight with injectable transport and pinned protocol fixture."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from thbison_v6.ledger import Clock

MANIFEST_NAME = "STAGING_ACCESS_MANIFEST.json"
PROTOCOL_FIXTURE = Path(__file__).resolve().parents[3] / "fixtures" / "staging" / "protocol.json"


def load_manifest(root: Path | None = None) -> dict:
    root = root or Path(__file__).resolve().parents[3]
    return json.loads((root / MANIFEST_NAME).read_text(encoding="utf-8"))


def load_protocol(path: Path | None = None) -> dict:
    path = path or PROTOCOL_FIXTURE
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def classify_http_error(status: int) -> str:
    if status in (401, 403):
        return "BLOCKED_ACCESS"
    if status == 404:
        return "BLOCKED_MISSING_INPUT"
    if status == 429:
        return "RATE_LIMITED"
    if status >= 500:
        return "UPSTREAM_ERROR"
    if status == 0:
        return "MALFORMED_RESPONSE"
    return "CLIENT_ERROR"


class FakeNotionTransport:
    """Deterministic Notion-like transport. Never contacts the network."""

    def __init__(self):
        self.pages: dict[str, list[dict]] = {}
        self.schema: dict[str, dict] = {}
        self.relation_targets: dict[str, str] = {}
        self.relation_pages: dict[str, list[dict]] = {}
        self.auth_ok = True
        self.force_429 = 0
        self.force_429_path: str | None = None
        self.calls = 0
        self.malformed = False
        self.cursor_loop = False
        self.missing_cursor = False
        self.page_size = 2
        self.retry_after = "0"

    def request(self, method: str, path: str, headers: dict, params: dict | None = None) -> dict:
        self.calls += 1
        if self.malformed:
            return {"status": 200, "json": None, "headers": {}}
        token = (headers.get("Authorization") or "").replace("Bearer ", "")
        if not token:
            return {"status": 401, "json": {"code": "unauthorized"}, "headers": {}}
        if not self.auth_ok:
            return {"status": 401, "json": {"code": "unauthorized"}, "headers": {}}
        if getattr(self, "forbid", False):
            return {"status": 403, "json": {"code": "forbidden"}, "headers": {}}
        if self.force_429 > 0 and (self.force_429_path is None or self.force_429_path in path):
            self.force_429 -= 1
            return {
                "status": 429,
                "json": {"code": "rate_limited"},
                "headers": {"Retry-After": self.retry_after},
            }
        if path.startswith("/v1/data_sources/") and path.endswith("/query"):
            ds = path.split("/")[3]
            start = (params or {}).get("start_cursor")
            rows = list(self.pages.get(ds, []))
            idx = int(start) if start and str(start).isdigit() else 0
            if self.cursor_loop and start:
                return {
                    "status": 200,
                    "json": {"results": rows[0:1], "next_cursor": start, "has_more": True},
                    "headers": {},
                }
            chunk = rows[idx : idx + self.page_size]
            more = idx + self.page_size < len(rows)
            nxt = str(idx + self.page_size) if more else None
            if more and self.missing_cursor:
                nxt = None
            return {
                "status": 200,
                "json": {"results": chunk, "next_cursor": nxt, "has_more": more},
                "headers": {},
            }
        if path.startswith("/v1/data_sources/") and method == "GET":
            ds = path.split("/")[3]
            props = dict(self.schema.get(ds, {}))
            return {"status": 200, "json": {"id": ds, "properties": props}, "headers": {}}
        if path.startswith("/v1/pages/") and path.endswith("/relations"):
            page_id = path.split("/")[3]
            start = (params or {}).get("start_cursor")
            rels = list(self.relation_pages.get(page_id, []))
            idx = int(start) if start and str(start).isdigit() else 0
            chunk = rels[idx : idx + self.page_size]
            more = idx + self.page_size < len(rels)
            nxt = str(idx + self.page_size) if more else None
            return {
                "status": 200,
                "json": {"results": chunk, "next_cursor": nxt, "has_more": more},
                "headers": {},
            }
        if path.startswith("/v1/pages/") and method == "GET":
            page_id = path.split("/")[3]
            parent = self.relation_targets.get(page_id, "UNKNOWN_PARENT")
            return {
                "status": 200,
                "json": {"id": page_id, "parent": {"page_id": parent}},
                "headers": {},
            }
        return {"status": 404, "json": {"code": "not_found"}, "headers": {}}


def _request_with_retry(transport, method, path, headers, params=None, clock: Clock | None = None, budget: int = 3) -> dict:
    attempts = 0
    clock = clock or Clock()
    while True:
        attempts += 1
        resp = transport.request(method, path, headers, params)
        if resp.get("status") == 429 and attempts <= budget:
            ra = (resp.get("headers") or {}).get("Retry-After", "0")
            try:
                clock.advance(float(ra))
            except Exception:
                clock.advance(0)
            continue
        return resp


def _paginate(transport, method, path, headers, clock, budget, max_pages: int) -> tuple[list, str | None]:
    rows: list = []
    cursor = None
    seen: set[str] = set()
    pages = 0
    while True:
        pages += 1
        if pages > max_pages:
            return rows, "PAGE_BUDGET"
        params = {"start_cursor": cursor} if cursor else {}
        resp = _request_with_retry(transport, method, path, headers, params, clock, budget)
        if resp.get("status") != 200:
            return rows, classify_http_error(resp.get("status", 0))
        body = resp.get("json")
        if not isinstance(body, dict):
            return rows, "MALFORMED_RESPONSE"
        batch = body.get("results")
        if not isinstance(batch, list):
            return rows, "MALFORMED_RESPONSE"
        rows.extend(batch)
        if not body.get("has_more"):
            return rows, None
        nxt = body.get("next_cursor")
        if not nxt:
            return rows, "MISSING_CURSOR"
        if nxt in seen:
            return rows, "CURSOR_LOOP"
        seen.add(str(nxt))
        cursor = nxt


def _row_project_id(row: dict) -> str | None:
    if row.get("project_id"):
        return row.get("project_id")
    props = row.get("properties") or {}
    proj = props.get("Project") or props.get("project_id")
    if isinstance(proj, dict):
        rich = proj.get("rich_text") or []
        if rich and isinstance(rich, list):
            return (rich[0].get("plain_text") or None)
        if "select" in proj and isinstance(proj["select"], dict):
            return proj["select"].get("name")
    if isinstance(proj, str):
        return proj
    return None


def _row_relation_ids(row: dict, prop: str) -> list[str]:
    if row.get("relation_page_id") and prop in {"Related", "relation_page_id"}:
        return [row["relation_page_id"]]
    props = row.get("properties") or {}
    node = props.get(prop) or {}
    rels = node.get("relation") if isinstance(node, dict) else None
    if not rels:
        return []
    out = []
    for item in rels:
        if isinstance(item, dict) and item.get("id"):
            out.append(item["id"])
        elif isinstance(item, str):
            out.append(item)
    return out


def run_preflight(
    transport,
    manifest: dict,
    token: str | None,
    project_id: str = "proj-lab",
    expected_relation_parent: str | None = None,
    protocol: dict | None = None,
    clock: Clock | None = None,
) -> dict:
    clock = clock or Clock()
    proto = protocol if protocol is not None else load_protocol()
    verified = False
    if not token:
        return {
            "status": "BLOCKED_ACCESS",
            "reason": "OUT_OF_BAND_SHORT_LIVED_NO_TOKEN_IN_PACKAGE",
            "live_calls": 0,
            "verified": False,
            "databases": [d["name"] for d in manifest.get("databases", [])],
        }
    if not proto or not proto.get("data_sources"):
        return {
            "status": "BLOCKED_OWNER_INPUT",
            "reason": "missing pinned protocol/expected schema fixture",
            "live_calls": 0,
            "verified": False,
        }
    required = proto.get("required_headers") or ["Authorization"]
    headers = {"Authorization": f"Bearer {token}"}
    missing_h = [h for h in required if h not in headers]
    if missing_h:
        return {"status": "CLIENT_ERROR", "reason": f"missing headers {missing_h}", "verified": False, "live_calls": 0}

    max_pages = int(proto.get("max_pages") or 8)
    budget = int(proto.get("retry_budget") or 3)
    expected_map = proto.get("data_sources") or {}
    allowlist = set(proto.get("relation_allowlist") or [])
    expected_parent = expected_relation_parent or proto.get("expected_relation_parent")
    findings: list[dict] = []

    for ds in manifest.get("databases", []):
        dsid = ds["data_source_id"]
        expected = expected_map.get(dsid)
        if expected is None:
            findings.append({"ds": dsid, "issue": "UNKNOWN", "detail": "no expected schema for DS"})
            return {
                "status": "BLOCKED_OWNER_INPUT",
                "reason": f"no expected schema for {dsid}",
                "findings": findings,
                "verified": False,
                "live_calls": 0,
                "protocol_pin": (proto.get("provenance") or {}).get("pin"),
            }
        schema_resp = _request_with_retry(
            transport, "GET", f"/v1/data_sources/{dsid}", headers, None, clock, budget
        )
        if schema_resp.get("status") != 200:
            return {
                "status": classify_http_error(schema_resp.get("status", 0)),
                "reason": schema_resp.get("json"),
                "live_calls": 0,
                "verified": False,
                "hop": "schema",
            }
        body = schema_resp.get("json")
        if not isinstance(body, dict) or "properties" not in body:
            return {"status": "MALFORMED_RESPONSE", "hop": "schema", "verified": False, "live_calls": 0}
        actual_props = body.get("properties") or {}
        for name, spec in (expected.get("properties") or {}).items():
            if name not in actual_props:
                findings.append({"ds": dsid, "issue": "MISSING_PROPERTY", "property": name})
                continue
            at = actual_props[name]
            atype = at.get("type") if isinstance(at, dict) else None
            if atype != spec.get("type"):
                findings.append(
                    {"ds": dsid, "issue": "TYPE_MISMATCH", "property": name, "expected": spec.get("type"), "actual": atype}
                )
            if spec.get("type") == "relation":
                dest = None
                if isinstance(at, dict):
                    dest = (at.get("relation") or {}).get("data_source_id") or at.get("relation_destination")
                if spec.get("relation_destination") and dest and dest != spec.get("relation_destination"):
                    findings.append({"ds": dsid, "issue": "MAPPING_MISMATCH", "property": name, "dest": dest})
        extra = set(actual_props) - set(expected.get("properties") or {})
        for e in extra:
            findings.append({"ds": dsid, "issue": "SCHEMA_DRIFT", "extra": e})

        rows, err = _paginate(
            transport, "POST", f"/v1/data_sources/{dsid}/query", headers, clock, budget, max_pages
        )
        if err:
            return {"status": err, "hop": "query", "verified": False, "live_calls": 0, "findings": findings}
        for row in rows:
            parent = (row.get("parent") or {}).get("data_source_id")
            if parent and parent != dsid:
                findings.append({"ds": dsid, "issue": "WRONG_PARENT_DS", "id": row.get("id"), "parent": parent})
            pid = _row_project_id(row)
            if pid and pid != project_id:
                findings.append({"ds": dsid, "issue": "PROJECT_SCOPE_LEAK", "id": row.get("id")})
            for pname, spec in (expected.get("properties") or {}).items():
                if spec.get("type") != "relation":
                    continue
                for rel_id in _row_relation_ids(row, pname):
                    page = _request_with_retry(
                        transport, "GET", f"/v1/pages/{rel_id}", headers, None, clock, budget
                    )
                    if page.get("status") in (401, 403, 429):
                        return {
                            "status": classify_http_error(page.get("status")),
                            "hop": "relation_target",
                            "verified": False,
                            "live_calls": 0,
                        }
                    if page.get("status") != 200 or not isinstance(page.get("json"), dict):
                        findings.append({"ds": dsid, "issue": "RELATION_FETCH_FAILED", "page": rel_id})
                        continue
                    tparent = (page["json"].get("parent") or {}).get("page_id")
                    if tparent is None:
                        findings.append({"ds": dsid, "issue": "MISSING_PARENT", "page": rel_id})
                        continue
                    if allowlist and tparent not in allowlist:
                        findings.append(
                            {"ds": dsid, "issue": "OUTSIDE_ALLOWLIST", "page": rel_id, "parent": tparent}
                        )
                    elif expected_parent and tparent != expected_parent:
                        findings.append(
                            {
                                "ds": dsid,
                                "issue": "BLOCKED_STAGING_RELATIONS",
                                "page": rel_id,
                                "parent": tparent,
                            }
                        )
                    rel_rows, rerr = _paginate(
                        transport, "GET", f"/v1/pages/{rel_id}/relations", headers, clock, budget, max_pages
                    )
                    if rerr:
                        return {"status": rerr, "hop": "relation_pagination", "verified": False, "live_calls": 0}

    blocked = {f["issue"] for f in findings}
    if "BLOCKED_STAGING_RELATIONS" in blocked or "OUTSIDE_ALLOWLIST" in blocked:
        status = "BLOCKED_STAGING_RELATIONS"
    elif "MISSING_PROPERTY" in blocked or "TYPE_MISMATCH" in blocked or "MAPPING_MISMATCH" in blocked or "SCHEMA_DRIFT" in blocked:
        status = "DRIFT"
    elif findings:
        status = "FINDINGS"
    else:
        status = "PREFLIGHT_OK_FAKE_TRANSPORT"
    return {
        "status": status,
        "verified": verified,
        "findings": findings,
        "live_calls": 0,
        "transport": "fake",
        "protocol_pin": (proto.get("provenance") or {}).get("pin"),
    }


def preflight_read_only() -> dict:
    token = os.environ.get("STAGING_NOTION_TOKEN", "").strip()
    enabled = os.environ.get("STAGING_ENABLED", "false").lower() == "true"
    manifest = load_manifest()
    if not enabled or not token:
        return {
            "status": "BLOCKED_ACCESS",
            "reason": "OUT_OF_BAND_SHORT_LIVED_NO_TOKEN_IN_PACKAGE",
            "live_calls": 0,
            "verified": False,
            "databases": [d["name"] for d in manifest.get("databases", [])],
        }
    return {
        "status": "NOT_RUN",
        "reason": "TOKEN_PRESENT_NOT_VERIFIED_NO_LIVE_CALL",
        "live_calls": 0,
        "verified": False,
    }
