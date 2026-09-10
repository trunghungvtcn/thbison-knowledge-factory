from __future__ import annotations

from kf_pilot.contractor_bridge.mapping import (
    CONTRACTOR_BASELINE,
    FACTORY_BASELINE,
    J1_REVIEWED,
    J2_PUBLISHED,
    PUBLIC_API_MAP,
    SYMBOL_MAP,
)


def test_baselines_are_full_shas() -> None:
    assert len(CONTRACTOR_BASELINE) == 40
    assert len(FACTORY_BASELINE) == 40
    assert CONTRACTOR_BASELINE == "afac091e60bb6c8a0f0630964e43f5e80951267c"
    assert FACTORY_BASELINE == "3f1f125f3ccb6b5fbf173c2aa0e10b5d3b30584b"
    assert J1_REVIEWED == "b9e291fb84ddf99a6e6dd662ae122f39326f4d41"
    assert J2_PUBLISHED == "5e6161914f519403059ce13a1568d58ac7162f28"


def test_public_api_covers_three_core_packages() -> None:
    names = set(PUBLIC_API_MAP)
    assert "grok_locator.LocatorResolver" in names
    assert "grok_asset_store.AssetStore" in names
    assert "grok_job_ledger.JobLedger" in names
    assert "grok_notion_projection.Projector" in names


def test_fingerprint_maps_to_admit() -> None:
    mapped = SYMBOL_MAP["RunContract.fingerprint"]["contractor"]
    assert "JobLedger.admit" in mapped
