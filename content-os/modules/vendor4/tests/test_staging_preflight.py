from app.staging_preflight import run_preflight


def test_k32_no_token_does_not_hardcode_blocked(monkeypatch):
    monkeypatch.delenv("STAGING_NOTION_TOKEN", raising=False)
    monkeypatch.delenv("STAGING_ENABLED", raising=False)
    report = run_preflight()
    assert report["status"] == "IMPLEMENTED_MOCK_READY"
    assert report["writes_attempted"] == 0
    assert report["production_writes"] == 0
    assert len(report["databases"]) == 4
