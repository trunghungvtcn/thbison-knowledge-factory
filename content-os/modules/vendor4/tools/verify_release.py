from __future__ import annotations

import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN = re.compile(r"(secret_[A-Za-z0-9]+|ntn_[A-Za-z0-9]+|PRODUCTION_TOKEN\s*=\s*\S+|n8n\.thbison|github\.com/trunghung)", re.I)
hits = []
for path in ROOT.rglob("*"):
    if path.is_file() and path.suffix.lower() not in {".zip", ".png", ".jpg"}:
        try:
            text = path.read_text(encoding="utf-8")
        except Exception:
            continue
        if FORBIDDEN.search(text):
            hits.append(str(path.relative_to(ROOT)))
print({"internal_reference_hits": hits})
sys.exit(1 if hits else 0)
