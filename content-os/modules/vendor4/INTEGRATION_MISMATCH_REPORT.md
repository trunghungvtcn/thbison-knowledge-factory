# Integration Mismatch Report

- Test run ID: local-mock
- Source revision: rev-synthetic-1
- Schema revision: schema-1.0.0
- Module/contract version: VENDOR_4 / 1.0.0
- Severity: LOW
- Expected: Staging round-trip against four Notion databases in STAGING_ACCESS_MANIFEST.json
- Actual: Credential not present in package (`OUT_OF_BAND_SHORT_LIVED_NO_TOKEN_IN_PACKAGE`). Staging tests NOT_RUN.
- Minimal reproduction: start service without STAGING_NOTION_TOKEN
- Affected entity/relation/property: Evidence Sources, Product Attributes, Knowledge Items, Canonical Knowledge
- Data migration impact: none
- Backward-compatible recommendation: inject short-lived token via env; keep fixtures synthetic
- Evidence files: docs/STAGING_ACCESS_MANIFEST.json
- Production touched: NO
