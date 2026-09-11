# Proposal — JobReceipt LEASED + capabilities service (OWNER OPEN)

Current mapping (not approved):
- Internal LEASED -> JobReceipt.status QUEUED
- Capabilities.service = content-workflow

Consumers affected: any client that treats QUEUED as not-yet-claimed; orchestrator workers using lease routes.

Compatibility test: tests/test_http_api.py projection + app/projection.py.

Do not treat this file as contract 1.0.0 change.
