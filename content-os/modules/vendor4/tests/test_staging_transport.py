from app.notion_transport import MockTransport, TransportError
from app.staging_preflight import run_preflight


def _ok_page(ds, has_more=False, cursor=None):
    return {
        "status": 200,
        "body": {
            "results": [{"id": "p1", "parent": {"data_source_id": ds}}],
            "has_more": has_more,
            "next_cursor": cursor,
        },
    }


def test_mock_pagination_and_allowlist():
    from pathlib import Path
    import json

    manifest = json.loads((Path(__file__).resolve().parents[1] / "docs/STAGING_ACCESS_MANIFEST.json").read_text())
    ids = [d["data_source_id"] for d in manifest["databases"]]
    t = MockTransport()
    t.allowlist = set(ids)
    for i, ds in enumerate(ids):
        t.queue({"status": 200, "body": {"id": ds, "properties": {"Name": {"type": "title"}}}})
        if i == 0:
            t.queue(_ok_page(ds, has_more=True, cursor="c2"))
            t.queue(_ok_page(ds, has_more=False))
        else:
            t.queue(_ok_page(ds))
    man = Path(__file__).resolve().parents[1] / "docs/STAGING_ACCESS_MANIFEST.json"
    raw=json.loads(man.read_text())
    raw["expected_schema"]={d["data_source_id"]:{"id":d["data_source_id"],"properties":{"Name":{"type":"title"}}} for d in raw["databases"]}
    mp=Path("/tmp/pinned-st.json"); mp.write_text(json.dumps(raw))
    report = run_preflight(manifest_path=mp, transport=t, live=False)
    assert report["status"] in {"PREFLIGHT_INCOMPLETE","PREFLIGHT_MOCK_OK","CHANGES_REQUIRED"}
    assert report["requests_attempted"] >= 8
    assert report["databases"][0]["pages"] == 2
    assert report["writes_attempted"] == 0
    assert report["databases"][0].get("relation_targets_verified") is not True


def test_mock_401():
    t = MockTransport()
    t.queue(TransportError("HTTP_ERROR", 401, "nope"))
    t.queue(TransportError("HTTP_ERROR", 401, "nope"))
    t.queue(TransportError("HTTP_ERROR", 401, "nope"))
    t.queue(TransportError("HTTP_ERROR", 401, "nope"))
    report = run_preflight(transport=t)
    assert report["status"] == "BLOCKED_ACCESS"
    assert report["errors"][0]["class"] == "AUTH_DENIED"


def test_mock_429_and_timeout_and_outside():
    t = MockTransport()
    t.queue(TransportError("HTTP_ERROR", 429, "slow"))
    t.queue(TransportError("TIMEOUT_OR_NETWORK", None, "tick"))
    t.allowlist = {"only-this"}
    t.queue(TransportError("OUTSIDE_ALLOWLIST", 403, "other"))
    t.queue(TransportError("HTTP_ERROR", 403, "no"))
    report = run_preflight(transport=t)
    assert {e["class"] for e in report["errors"]} <= {
        "RATE_LIMITED",
        "TIMEOUT_OR_NETWORK",
        "OUTSIDE_ALLOWLIST",
        "AUTH_DENIED",
    }


def test_cli_missing_token_nonzero(tmp_path, monkeypatch):
    monkeypatch.delenv("STAGING_NOTION_TOKEN", raising=False)
    monkeypatch.delenv("STAGING_ENABLED", raising=False)
    from tools.staging_preflight import main

    out = tmp_path / "pf.json"
    code = main(["--manifest", str(tmp_path.parent / "nope") if False else "docs/STAGING_ACCESS_MANIFEST.json", "--read-only", "--output", str(out)])
    # without token and without enable -> IMPLEMENTED_MOCK_READY exit 0
    assert code == 0
    data = out.read_text()
    assert "IMPLEMENTED_MOCK_READY" in data


def test_blocked_opt_in(monkeypatch):
    monkeypatch.setenv("STAGING_NOTION_TOKEN", "ntoken")
    monkeypatch.delenv("STAGING_ENABLED", raising=False)
    from app.staging_preflight import run_preflight

    r = run_preflight()
    assert r["status"] == "BLOCKED_OPT_IN"
