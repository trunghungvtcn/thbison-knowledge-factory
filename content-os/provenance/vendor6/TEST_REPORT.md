# TEST_REPORT — FINAL

acceptance_claimed: false  
code_changed: false  
Tests were not re-run for this package. Counts below are the R2 vendor run and the reviewer confirmation of the same frozen source.

## Same-run vendor (R2 source, not re-executed here)
command: `PYTHONPATH=src python3 -m pytest tests -q --junitxml=evidence/junit.xml`  
Python 3.10.21 / pytest 8.3.3 / jsonschema 4.23.0 / exit 0  
JUnit: 73 collected, 71 passed, 2 skipped, 0 failed  
Skips: INT-26 (actual Planning→CMS E2E NOT_RUN), INT-27 (no paired benchmark)  
Evidence: `evidence/vendor_r2/junit.xml`, `evidence/vendor_r2/pytest_all.log`

## Reviewer confirmation (same source, different machine)
Python 3.12.14 / pytest 8.3.3  
73 collected, 71 passed, 2 skipped  
Evidence: `evidence/reviewer/pytest.txt`, `evidence/reviewer/junit.xml`  
Environment: preinstalled; G1 clean install still BLOCKED_ENVIRONMENT.

## Layer results (do not promote)

| Layer | Count / gate | Result |
|---|---|---|
| Fake protocol (staging FakeNotionTransport) | 21 tests in test_staging_transport.py | mock PASS only; verified=false |
| Spy dispatch / fake HTTP | test_dispatch + adapter_modes | mock PASS; verified_component=false |
| REFERENCE_ONLY simulators / contract | INT matrix + contract tests | PASS (mock) |
| Actual vendor processes | INT-26 | NOT_RUN / SKIP |
| Live staging | preflight_read_only / no token | BLOCKED_ACCESS |
| Benchmark | INT-27 | NOT_RUN / SKIP |
| G1 clean venv | ensurepip | BLOCKED_ENVIRONMENT |

71 PASS does not close R2-03, actual E2E, live staging, or G1.
