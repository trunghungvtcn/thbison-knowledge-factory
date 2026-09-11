# INTERNAL_TAKEOVER.md — Vendor 5

Vendor closeout does not request new vendor work for missing inputs.

## 1. Actual CMS endpoint / credentials / allowlist

Need: staging URL on allowlist, service credential, destination IDs, project IDs matching contract.
Done when: inspectCapabilities returns non-simulator provider identity; one STAGING_DRAFT create+rollbackOwnTestMutation on real CMS; LIVE remains denied until owner enablement.

## 2. Native CMS implementation gap

Current: DurableCmsSimulator + SQLite ledger. Native HTTP client is not in this source.
Done when: a separate scoped job implements native transport against frozen contract 1.0.0.

## 3. Actual Vendor 3 retry integration

Current: local RuntimeRetryPort class with owner='vendor3'.
Need: Vendor 3 module API, import path, retry budget contract.
Done when: adapter calls the real port; nested retry storms still bounded.

## 4. Canonical hash golden vectors (upstream)

Current: hash profile matches contract examples.
Need: owner-signed golden vectors if integration requires bit-for-bit match with other vendors.

## 5. Live rollback / deployment

Out of vendor scope. Internal decides deploy, monitoring, and rollback of own test mutations.

## 6. DEFERRED_INTERNAL

- Richer HTML sanitizer (html5lib) instead of regex.
- Additional Python architectures/OS in wheelhouse.
- HTTP surface beyond the five CMSPort methods.
- Performance / style / extra edge-case tests.

## Reproduction (offline)

```
unzip source.zip
cd v5src
bash scripts/verify_local.sh
# expect VERIFY_LOCAL_OK
python -m pytest tests/test_verify_fail_closed.py tests/test_r2_policy.py -q
```

Policy mismatch: set approval.policy_version to `different-policy` then publish DRY_RUN → AdapterError POLICY_MISMATCH, zero provider calls.
