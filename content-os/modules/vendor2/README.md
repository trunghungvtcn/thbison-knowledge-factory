# THBISON Vendor 2 — Content OS (MOCK / SYNTHETIC)

Independent contractor drop. Simulation only.

This is **not** acceptance-complete. Kit self-test is **PARTIAL** (50 passed, 1 failed: `test_naive_date_rejected`). Flags `ADAPTER_VERIFIED` and `INTEGRATED_CANARY_PASS` are **not** claimed.

## Run (mock)

```bash
npm ci
CONTENT_OS_MODE=MOCK npm run dev
```

Listens on `0.0.0.0:8080`. Health: `GET /healthz`.

Demo tokens (TEST_ONLY): see [config/environment.example.json](config/environment.example.json).

## Honest labels

| Label | Value |
|-------|-------|
| KIT_SELF_TEST | PARTIAL |
| P05 15% vs Vendor 1 | NOT_MET |
| P08 | SYNTHETIC |
| S01–S18 | NOT_RUN (Vendor 1) |
| A1–A8 | BLOCKED_EXTERNAL |
| Real provider probe | NOT_RUN_EXTERNAL |
| Docker image | NOT_BUILT |

Do not treat mock/synthetic results as successful live integration.

## Docs

- [docs/OPERATOR_RUNBOOK.md](docs/OPERATOR_RUNBOOK.md)
- [docs/KNOWN_LIMITATIONS.md](docs/KNOWN_LIMITATIONS.md)
- [docs/DELIVERY_RECEIPT.json](docs/DELIVERY_RECEIPT.json)
- [docs/SCOPE_STATUS.json](docs/SCOPE_STATUS.json)
- [docs/REVIEW_RESPONSE.md](docs/REVIEW_RESPONSE.md)

## Tests

```bash
npm test
node tests/acceptance/http.mjs
cd vendor-kit && python3 -m pytest tests/test_contracts.py -v
```

Kit tests are **unmodified**. The known jsonschema vs `TIMEZONE_REQUIRED` failure remains.

## Pack

```bash
node scripts/pack-release.mjs
```

Produces `releases/THBISON-VENDOR-2-CONTENT-OS-release.zip` plus a sidecar `.sha256`.
