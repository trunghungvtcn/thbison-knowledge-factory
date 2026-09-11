"""Integrity check for distributed kit; excludes this receipt from self-hashing."""
import hashlib, json, sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'KIT_MANIFEST.json').read_text(encoding='utf-8'))
fail=[]
for entry in manifest['files']:
    p=ROOT/entry['path']
    if not p.is_file():fail.append({'path':entry['path'],'error':'MISSING'});continue
    blob=p.read_bytes()
    if len(blob)!=entry['bytes'] or hashlib.sha256(blob).hexdigest()!=entry['sha256']:
        fail.append({'path':entry['path'],'error':'HASH_OR_SIZE_MISMATCH'})
print(json.dumps({'status':'KIT_INTEGRITY_PASS' if not fail else 'FAIL','checked':len(manifest['files']),'failures':fail},indent=2))
sys.exit(bool(fail))
