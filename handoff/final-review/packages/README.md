# Packages

Each job ZIP is a GitHub-required guidance pack (not offline-complete).

Contents (same order used when packing):

`COMMON_RULES.md` `BASELINES.json` `PROMPT.md` `ACCEPTANCE.md` `SOURCE.txt`

SHA256SUMS.txt (bytes of the three ZIPs attached to the prerelease):

```
fd611f749e9102feb76ea8e06eb0d617d18fae6713d60e82f027e5bc1bb18d21  J1-final-fix.zip
c3dd40e82ca7d37c6a356e0bfb613d8cae73ae11469a39e1ba875a5a6c0e6705  J2-final-fix.zip
c0fea0246dadcbd458b4fed75635a466d7ac8421a5980df31aafeeb2e7af7364  J3-final-fix.zip
```

Built with Python `zipfile.ZIP_DEFLATED` (Info-ZIP `zip` not available in the publisher sandbox). Unpacked sources live in `packages/J*-final-fix/`. Binary ZIPs are gitignored and published only as GitHub Release assets.

Tag: `handoff-j1-j3-final-20260910`.
