"""Local allowlisted delivery bundles. Never upload or include credentials."""
from pathlib import Path
import hashlib
import zipfile
import json
import re

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'v165/delivery'


def bundle(name,paths):
    destination=OUT/name
    if destination.exists():raise ValueError('OUTPUT_ALREADY_EXISTS')
    manifest={}
    with zipfile.ZipFile(destination,'x',zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(set(paths)):
            if not path.is_file():raise ValueError('Missing allowlisted file: '+str(path))
            rel=path.relative_to(ROOT).as_posix()
            if any(s in rel.lower() for s in ('token','secret','credential','__pycache__','.env')):
                raise ValueError('Forbidden archive path')
            raw=path.read_bytes()
            if re.search(rb'(?:KGAT_[A-Za-z0-9]{20,}|ntn_[A-Za-z0-9]{20,})',raw):
                raise ValueError('Credential marker detected')
            manifest[rel]=hashlib.sha256(raw).hexdigest();archive.writestr(rel,raw)
        archive.writestr('BUNDLE_MANIFEST.json',json.dumps(manifest,sort_keys=True,indent=2))
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:raise ValueError('ZIP_INTEGRITY_FAIL')
        for path,h in manifest.items():
            if hashlib.sha256(archive.read(path)).hexdigest()!=h:raise ValueError('BUNDLE_HASH_FAIL')
    return {'path':str(destination),'sha256':hashlib.sha256(destination.read_bytes()).hexdigest(),'files':len(manifest)}


def main():
    OUT.mkdir(exist_ok=True)
    code=list((ROOT/'src/kf_pilot/v165_complete_record').glob('*.py'))
    code += [ROOT/'tests/test_v165_complete_record.py',ROOT/'v165/README.md',ROOT/'v165/ACCEPTANCE_COVERAGE.md',Path(__file__)]
    code += list((ROOT/'v165/logs').glob('*.txt'))
    code += [ROOT/'v165/V165_EXECUTION_REPORT.md']
    private=list((ROOT/'v165/artifacts/final-001').glob('*'))+list((ROOT/'v165/artifacts/replay-001').glob('*'))
    private += list((ROOT/'v165/inputs').glob('*.json'))+list((ROOT/'v165/audit').glob('*.png'))
    print(json.dumps([bundle('V16.5-code-tests-report.zip',code),
                     bundle('V16.5-audit-PRIVATE-LOCAL-ONLY.zip',private)],indent=2))


if __name__=='__main__':main()
