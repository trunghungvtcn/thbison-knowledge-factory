# Vendor 6 harness runbook (R1)

## Commands
```
# 1) environment (may BLOCKED_ENVIRONMENT if no ensurepip)
./scripts/verify_local

# 2) tests only (deps already present)
./scripts/run_tests

# reviewer reproduction
python3 scripts/reproduce.py /absolute/path/to/source-root
```

Dependencies: `pip install -r requirements-dev.txt` (jsonschema==4.23.0, pytest==8.3.3). Wheelhouse not bundled; clean install needs network or a provided wheelhouse.

## Modes
REFERENCE_ONLY default. ACTUAL_COMPONENTS raises MISSING_ADAPTER without HTTP/process adapters for every hop. MIXED requires stub_hops declaration plus ACTUAL bindings for the rest.

## Staging
No token in package. Live: BLOCKED_ACCESS. Fake transport tests never imply VERIFIED.
