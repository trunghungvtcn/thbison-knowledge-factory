"""Read-only Notion staging preflight with fail-closed parent/relation checks.

Protocol: Notion-Version 2025-09-03 and /v1/data_sources/{id}/query.
Data sources API was introduced in 2025-09-03.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any

DEFAULT_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2025-09-03"


class TransportError(Exception):
    def __init__(self, status: int, body: str = "", headers: dict | None = None, kind: str | None = None):
        super().__init__(kind or f"http {status}")
        self.status = status
        self.body = body
        self.headers = headers or {}
        self.kind = kind


class PreflightClosed(Exception):
    def __init__(self, kind: str, message: str, extra: dict | None = None):
        super().__init__(message)
        self.kind = kind
        self.extra = extra or {}


class UrlLibTransport:
    def request(self, method: str, url: str, headers: dict[str, str], body: bytes | None = None) -> tuple[int, dict[str, str], bytes]:
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                return resp.status, {k.lower(): v for k, v in resp.headers.items()}, resp.read()
        except urllib.error.HTTPError as e:
            raw = e.read() if e.fp else b""
            raise TransportError(e.code, raw.decode("utf-8", "replace"), {k.lower(): v for k, v in e.headers.items()}) from e
        except TimeoutError as e:
            raise TransportError(598, "timeout", kind="TIMEOUT") from e
        except Exception as e:
            raise TransportError(599, str(e), kind="TRANSPORT") from e


class StagingClient:
    def __init__(self, manifest: dict, token: str | None, transport: Any | None = None, enabled: bool = False, read_only: bool = True) -> None:
        self.manifest = manifest
        self.token = token
        self.transport = transport or UrlLibTransport()
        self.enabled = enabled
        self.read_only = read_only
        self.allow = {d["data_source_id"] for d in manifest.get("databases", [])}
        self.requests: list[dict] = []
        self.max_requests = int(manifest.get("max_provider_requests") or 40)
        raw_expected = manifest.get("expected_schema")
        if raw_expected is None:
            self.expected_schema = {}
            self.expected_meta = {}
        elif isinstance(raw_expected, dict) and "databases" in raw_expected:
            self.expected_schema = raw_expected.get("databases") or {}
            self.expected_meta = {k: raw_expected.get(k) for k in ("version", "digest", "provenance", "source")}
        else:
            self.expected_schema = raw_expected or {}
            self.expected_meta = {}

    def classify(self, status: int | None, kind: str | None = None) -> str:
        if kind:
            return kind
        if status in (401, 403):
            return "AUTH_DENIED"
        if status == 429:
            return "RATE_LIMITED"
        if status == 404:
            return "NOT_FOUND"
        if status == 598:
            return "TIMEOUT"
        if status and status >= 500:
            return "PROVIDER_ERROR"
        return "OK"

    def _headers(self) -> dict[str, str]:
        h = {"Notion-Version": NOTION_VERSION, "Content-Type": "application/json"}
        if self.token:
            h["Authorization"] = f"Bearer {self.token}"
        return h

    def _call(self, method: str, path: str, payload: dict | None = None) -> dict:
        url = path if path.startswith("http") else DEFAULT_BASE + path
        body = json.dumps(payload).encode() if payload is not None else None
        rec: dict[str, Any] = {"method": method, "url": url, "path": path, "notion_version": NOTION_VERSION, "has_auth": bool(self.token)}
        try:
            status, headers, raw = self.transport.request(method, url, self._headers(), body)
            rec["status"] = status
            rec["sent_notion_version"] = self._headers()["Notion-Version"]
            self.requests.append(rec)
            if len(self.requests) > self.max_requests:
                raise PreflightClosed("BUDGET_EXCEEDED", f"provider requests exceeded {self.max_requests}")
            if status >= 400:
                raise TransportError(status, raw.decode("utf-8", "replace"), headers)
            if not raw:
                raise PreflightClosed("MALFORMED_RESPONSE", "empty body")
            try:
                return json.loads(raw.decode("utf-8"))
            except json.JSONDecodeError as e:
                raise PreflightClosed("MALFORMED_RESPONSE", "invalid json") from e
        except TransportError as e:
            rec["status"] = e.status
            rec["error"] = self.classify(e.status, e.kind)
            if "retry-after" in (e.headers or {}):
                rec["retry_after"] = e.headers["retry-after"]
            self.requests.append(rec)
            raise

    def assert_allowlisted(self, data_source_id: str) -> None:
        if data_source_id not in self.allow:
            raise PreflightClosed("ALLOWLIST_DENIED", f"target outside allowlist: {data_source_id}")

    def fetch_schema(self, data_source_id: str) -> dict:
        self.assert_allowlisted(data_source_id)
        data = self._call("GET", f"/data_sources/{data_source_id}")
        if not isinstance(data, dict):
            raise PreflightClosed("SCHEMA_DRIFT", "schema not an object")
        if "properties" not in data or not isinstance(data.get("properties"), dict):
            raise PreflightClosed("SCHEMA_DRIFT", "schema missing properties object")
        expected = self.expected_schema.get(data_source_id)
        if expected:
            if expected.get("id") and expected["id"] != data.get("id"):
                raise PreflightClosed("SCHEMA_DRIFT", "schema id mismatch")
            exp_props = expected.get("properties") or {}
            for name, spec in exp_props.items():
                got = data["properties"].get(name)
                if not got:
                    raise PreflightClosed("SCHEMA_DRIFT", f"missing expected property {name}")
                if spec.get("type") and got.get("type") != spec.get("type"):
                    raise PreflightClosed("SCHEMA_DRIFT", f"property type drift {name}")
                if spec.get("id") and got.get("id") != spec.get("id"):
                    raise PreflightClosed("SCHEMA_DRIFT", f"property id drift {name}")
                exp_dest = self.expected_relation_ds(spec)
                got_dest = self.expected_relation_ds(got)
                if spec.get("type") == "relation" or exp_dest or got_dest:
                    if not exp_dest:
                        raise PreflightClosed("BLOCKED_OWNER_INPUT", f"expected mapping missing destination for {name}")
                    if got_dest != exp_dest:
                        raise PreflightClosed("SCHEMA_DRIFT", f"relation destination drift {name}: provider={got_dest} expected={exp_dest}")
        return data

    def query_data_source(self, data_source_id: str, start_cursor: str | None = None) -> dict:
        self.assert_allowlisted(data_source_id)
        payload: dict[str, Any] = {"page_size": 100}
        if start_cursor:
            payload["start_cursor"] = start_cursor
        return self._call("POST", f"/data_sources/{data_source_id}/query", payload)

    def paginate(self, data_source_id: str) -> list[dict]:
        pages: list[dict] = []
        cursor = None
        seen: set[str] = set()
        while True:
            data = self.query_data_source(data_source_id, cursor)
            if not isinstance(data, dict) or "results" not in data:
                raise PreflightClosed("MALFORMED_RESPONSE", "query missing results")
            pages.extend(data.get("results") or [])
            if not data.get("has_more"):
                break
            nxt = data.get("next_cursor")
            if not nxt:
                raise PreflightClosed("MISSING_CURSOR", "has_more true without next_cursor")
            if nxt in seen:
                raise PreflightClosed("CURSOR_LOOP", "repeated next_cursor")
            seen.add(nxt)
            cursor = nxt
        return pages

    def retrieve_page(self, page_id: str) -> dict:
        return self._call("GET", f"/pages/{page_id}")

    def retrieve_property(self, page_id: str, property_id: str, start_cursor: str | None = None) -> dict:
        from urllib.parse import quote
        path = f"/pages/{quote(str(page_id), safe='')}/properties/{quote(str(property_id), safe='')}"
        if start_cursor:
            path += f"?start_cursor={quote(str(start_cursor), safe='')}"
        return self._call("GET", path)

    def parent_ds(self, page: dict) -> str | None:
        parent = page.get("parent") or {}
        return parent.get("data_source_id") or parent.get("database_id")

    def parent_ok(self, page: dict, expected_ds: str) -> bool:
        return self.parent_ds(page) == expected_ds

    def relation_ids_from_prop(self, prop: dict) -> tuple[list[str], bool, str | None]:
        if not isinstance(prop, dict):
            return [], False, None
        rel = prop.get("relation")
        if rel is None and prop.get("object") == "list":
            rel = prop.get("results") or []
            ids = [x.get("id") for x in rel if isinstance(x, dict) and x.get("id")]
            return ids, bool(prop.get("has_more")), prop.get("next_cursor")
        if rel is None:
            return [], False, None
        ids = [x.get("id") for x in rel if isinstance(x, dict) and x.get("id")]
        return ids, bool(prop.get("has_more")), prop.get("next_cursor")

    def expected_relation_ds(self, schema_prop: dict) -> str | None:
        rel = schema_prop.get("relation") if isinstance(schema_prop, dict) else None
        if isinstance(rel, dict):
            return rel.get("data_source_id") or rel.get("database_id")
        return None

    def collect_relation_targets(self, row: dict, schema: dict) -> list[tuple[str, str, str]]:
        """Yield (property_name, expected_ds, target_id). Fail closed on truncated pages."""
        row_props = row.get("properties") or {}
        schema_props = schema.get("properties") or {}
        out: list[tuple[str, str, str]] = []
        for name, spec in schema_props.items():
            if not isinstance(spec, dict) or spec.get("type") != "relation":
                continue
            trusted = None
            pin = (self.expected_schema.get(schema.get("id")) or self.expected_schema.get(row.get("parent", {}).get("data_source_id")) or {})
            pin_prop = (pin.get("properties") or {}).get(name)
            if pin_prop:
                trusted = self.expected_relation_ds(pin_prop)
            expected_ds = trusted or self.expected_relation_ds(spec)
            if self.expected_schema and not trusted:
                raise PreflightClosed("BLOCKED_OWNER_INPUT", f"no trusted destination mapping for {name}")
            if not expected_ds:
                raise PreflightClosed("BLOCKED_OWNER_INPUT", f"relation {name} has no target data_source_id in schema")
            prop = row_props.get(name)
            if prop is None:
                raise PreflightClosed("MISSING_RELATION_PROPERTY", f"row missing schema relation {name}")
            ids, has_more, cursor = self.relation_ids_from_prop(prop)
            if has_more:
                pid = row.get("id")
                prop_id = prop.get("id") or spec.get("id") or name
                if not cursor:
                    raise PreflightClosed("MISSING_CURSOR", "relation has_more without cursor")
                if not pid or not prop_id:
                    raise PreflightClosed("RELATION_TRUNCATED", "relation has_more but cannot page")
                seen: set[str] = set()
                pages = 0
                while has_more:
                    pages += 1
                    if pages > self.max_requests:
                        raise PreflightClosed("BUDGET_EXCEEDED", "relation pagination budget")
                    if cursor in seen:
                        raise PreflightClosed("CURSOR_LOOP", "relation cursor loop")
                    seen.add(cursor)
                    page = self.retrieve_property(pid, prop_id, cursor)
                    more_ids, has_more, cursor = self.relation_ids_from_prop(page)
                    ids.extend(more_ids)
                    if has_more and not cursor:
                        raise PreflightClosed("MISSING_CURSOR", "paged relation missing cursor")
            for tid in ids:
                out.append((name, expected_ds, tid))
        return out


def resolve_token() -> tuple[str | None, str]:
    for name in ("STAGING_NOTION_TOKEN", "NOTION_STAGING_TOKEN", "STAGING_TOKEN"):
        val = os.getenv(name)
        if val:
            return val, name
    return None, ""


def _write(path: str | None, report: dict) -> None:
    if not path:
        return
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
        f.write("\n")


def run_preflight(manifest: dict, output_path: str | None = None, read_only: bool = True, transport: Any | None = None) -> tuple[int, dict]:
    token, token_src = resolve_token()
    enabled = os.getenv("STAGING_ENABLED", "false").lower() == "true"
    report: dict[str, Any] = {
        "read_only": read_only,
        "token_present": bool(token),
        "token_source": token_src or None,
        "staging_enabled": enabled,
        "notion_version": NOTION_VERSION,
        "databases": [{"name": d.get("name"), "data_source_id": d.get("data_source_id")} for d in manifest.get("databases", [])],
        "production_writes": "DENIED",
        "runtime_ledger": "local_sqlite_not_notion",
        "requests": [],
        "verified": False,
        "relation_status": "UNKNOWN",
    }
    if not token:
        report["status"] = "BLOCKED_ACCESS"
        report["reason"] = "STAGING_NOTION_TOKEN missing"
        _write(output_path, report)
        return 2, report
    if not enabled:
        report["status"] = "BLOCKED_OPT_IN"
        report["reason"] = "token present but STAGING_ENABLED!=true"
        _write(output_path, report)
        return 3, report

    client = StagingClient(manifest, token, transport=transport or UrlLibTransport(), enabled=True, read_only=read_only)
    try:
        snapshots = []
        relation_findings = []
        coverage = []
        observed_rel_props = 0
        observed_targets = 0
        empty_db = False
        for ds in manifest.get("databases", []):
            dsid = ds["data_source_id"]
            schema = client.fetch_schema(dsid)
            rel_props = {n: s for n, s in (schema.get("properties") or {}).items() if isinstance(s, dict) and s.get("type") == "relation"}
            rows = client.paginate(dsid)
            if rel_props and not rows:
                empty_db = True
            cov = {"data_source_id": dsid, "relation_properties": list(rel_props), "rows": len(rows), "targets": 0}
            for row in rows:
                if not isinstance(row, dict) or "parent" not in row:
                    raise PreflightClosed("NO_PARENT", f"row missing parent in {dsid}")
                if not client.parent_ok(row, dsid):
                    raise PreflightClosed("WRONG_ROW_DS", "row parent is not expected data source", {"row_id": row.get("id"), "expected": dsid, "actual": client.parent_ds(row)})
                triples = client.collect_relation_targets(row, schema)
                if rel_props:
                    observed_rel_props += 1
                for name, expected_ds, tid in triples:
                    observed_targets += 1
                    cov["targets"] += 1
                    try:
                        page = client.retrieve_page(tid)
                    except TransportError as e:
                        if e.status == 404:
                            raise PreflightClosed("TARGET_INACCESSIBLE", f"relation target 404 {tid}") from e
                        raise
                    parent = client.parent_ds(page)
                    if not parent:
                        raise PreflightClosed("NO_PARENT", f"target {tid} missing parent")
                    if parent not in client.allow:
                        raise PreflightClosed("BLOCKED_STAGING_RELATIONS", "relation target parent outside staging allowlist", {"target": tid, "parent": parent, "property": name})
                    if parent != expected_ds:
                        raise PreflightClosed(
                            "WRONG_RELATION_TARGET",
                            "relation target parent does not match schema mapping",
                            {"target": tid, "parent": parent, "expected_ds": expected_ds, "property": name},
                        )
                    relation_findings.append({"target": tid, "parent": parent, "expected_ds": expected_ds, "property": name, "ok": True})
            coverage.append(cov)
            snapshots.append({"data_source_id": dsid, "name": ds.get("name"), "row_count": len(rows), "schema_ok": True})
        report["requests"] = client.requests
        report["snapshots"] = snapshots
        report["relation_findings"] = relation_findings
        report["coverage"] = coverage
        report["expected_schema_meta"] = getattr(client, "expected_meta", {})
        report["expected_schema_present"] = bool(client.expected_schema)
        if empty_db or observed_targets == 0:
            report["relation_status"] = "INCOMPLETE"
            report["status"] = "INCOMPLETE"
            report["verified"] = False
            report["reason"] = "empty database or no observed relation targets; not verified"
            _write(output_path, report)
            return 6, report
        if not client.expected_schema:
            report["relation_status"] = "INCOMPLETE"
            report["status"] = "BLOCKED_OWNER_INPUT"
            report["verified"] = False
            report["reason"] = "no trusted expected_schema pin; observed mapping is not THBISON-verified"
            _write(output_path, report)
            return 8, report
        report["relation_status"] = "VERIFIED"
        report["status"] = "READ_OK"
        report["verified"] = True
        _write(output_path, report)
        return 0, report
    except PreflightClosed as e:
        report["requests"] = client.requests
        report["status"] = e.kind
        report["verified"] = False
        report["reason"] = str(e)
        report["detail"] = e.extra
        _write(output_path, report)
        return 7, report
    except TransportError as e:
        report["requests"] = client.requests
        report["status"] = client.classify(e.status, e.kind)
        report["verified"] = False
        report["http_status"] = e.status
        _write(output_path, report)
        return 4, report
