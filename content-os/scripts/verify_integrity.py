#!/usr/bin/env python3
from pathlib import Path
import hashlib,sys
root=Path(__file__).resolve().parents[1];bad=[]
for line in (root/'SHA256SUMS.txt').read_text().splitlines():
 digest,name=line.split('  ',1);path=root/name
 if not path.resolve().is_relative_to(root.resolve()) or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest()!=digest:bad.append(name)
print('INTEGRITY_OK' if not bad else 'INTEGRITY_FAILED: '+', '.join(bad));sys.exit(bool(bad))
