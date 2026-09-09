#!/usr/bin/env python3
"""Build a deterministic handoff ZIP, never a production deployment package."""
import hashlib
from pathlib import Path
import zipfile
from verify_handoff import ROOT, verify

ALLOWLIST = [
    'README.md', 'PROMPT_CODEX_V165.md', 'IMPLEMENTATION_PLAN.md',
    'contracts/COMPLETE_RECORD_V1.md', 'contracts/contract_activation.template.json',
    'docs/ACCEPTANCE_MATRIX.md', 'docs/EXPECTED_REPORT.md', 'docs/VERIFICATION_SCOPE.md',
    'reference/final-003.zip', 'reference/targets.json',
    'reference/checkpoint_verification.json', 'scripts/verify_handoff.py',
    'scripts/build_zip.py',
]


def build():
    verify()
    contents = {name: (ROOT / name).read_bytes() for name in sorted(ALLOWLIST)}
    hashes = ''.join(hashlib.sha256(data).hexdigest() + '  ' + name + '\n'
                     for name, data in contents.items()).encode('utf-8')
    contents['SHA256SUMS.txt'] = hashes
    destination = ROOT.parent / 'V16.5-complete-record-plan-codex.zip'
    with zipfile.ZipFile(destination, 'w', compression=zipfile.ZIP_DEFLATED) as archive:
        for name, data in sorted(contents.items()):
            info = zipfile.ZipInfo('v165-codex-handoff/' + name, (2026, 9, 5, 0, 0, 0))
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            archive.writestr(info, data)
    with zipfile.ZipFile(destination) as archive:
        if archive.testzip() is not None:
            raise ValueError('OUTPUT_ZIP_CRC_FAILED')
        for name, data in contents.items():
            if archive.read('v165-codex-handoff/' + name) != data:
                raise ValueError('OUTPUT_BYTES_MISMATCH: ' + name)
    print(destination)
    print('files=' + str(len(contents)))
    print('sha256=' + hashlib.sha256(destination.read_bytes()).hexdigest())


if __name__ == '__main__':
    build()
