# Packages

Binary ZIPs were built with `zip -X` (no extra metadata) from the sibling unpacked directories.

SHA256SUMS.txt:

```
f0cd14db1689490cc1934236bf32d98e4481a609a387a8a39993ce4c85cdf63d  J1-final-fix.zip
1a9a2993f89a3093b6efd3bff5e6bbe5850e96aa2d1cad8c8a5662b05c40222a  J2-final-fix.zip
fe1247d72d753791826df47c19430dc6400dd9b54561ac3eefc26d7e2977c3ad  J3-final-fix.zip
```

Rebuild (must use `zip -X` and the same file set):

```
cd J1-final-fix && zip -X ../J1-final-fix.zip COMMON_RULES.md BASELINES.json PROMPT.md ACCEPTANCE.md SOURCE.txt
```

GitHub-resident form is this unpacked tree plus SHA256SUMS. Binary zips cannot be pushed through the text file API used in this session. Tag requested: `handoff-j1-j3-final-20260910`. Do not claim offline-complete.
