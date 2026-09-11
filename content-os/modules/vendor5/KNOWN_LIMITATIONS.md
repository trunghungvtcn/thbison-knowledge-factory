# KNOWN_LIMITATIONS R2

- Supported runtime: CPython 3.10, 3.11, 3.12 x86_64 with vendored rpds-py wheels. Other ABI → BLOCKED_ENVIRONMENT.
- No native CMS probe.
- RuntimeRetryPort is not an actual Vendor3 client.
- verify_local fail-closed tests use VERIFY_INJECT_FAIL (not for production runs).
- HTML sanitizer regex-only.
