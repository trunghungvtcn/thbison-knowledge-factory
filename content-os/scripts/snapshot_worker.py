"""Credential-free snapshot QA for Kaggle/Colab. No network or remote writes."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

SOURCES = {
    '87318868-8be2-4e27-8ab6-7a3d0b53bb32': 'evidence',
    'a4812f47-e1a6-4aa1-a619-558a79a4c4ff': 'products',
    '9d53865d-0cdd-41f3-a6c6-5d171b4e50f4': 'knowledge',
}

def inspect(raw, expected_hash):
    actual = hashlib.sha256(raw).hexdigest()
    if not re.fullmatch('[a-f0-9]{64}', expected_hash) or actual != expected_hash:
        raise ValueError('INPUT_HASH_MISMATCH')
    if len(raw) > 10 * 1024 * 1024:
        raise ValueError('INPUT_TOO_LARGE')
    data = json.loads(raw)
    if data.get('schema_version') != '1.0.0' or data.get('source') != 'notion-mcp-readonly':
        raise ValueError('INVALID_ENVELOPE')
    collections = data.get('collections', [])
    if len(collections) != 3 or {c['data_source_id'] for c in collections} != set(SOURCES):
        raise ValueError('COLLECTION_ALLOWLIST_MISMATCH')
    counts, states = {}, {}
    for collection in collections:
        label = SOURCES[collection['data_source_id']]
        rows = collection['rows']
        ids = [r['record_id'] for r in rows]
        if len(set(ids)) != len(ids) or any(not re.fullmatch(r'[a-fA-F0-9]{32}|[a-fA-F0-9]{8}(?:-[a-fA-F0-9]{4}){3}-[a-fA-F0-9]{12}', i) for i in ids):
            raise ValueError('INVALID_OR_DUPLICATE_ID')
        counts[label] = len(rows)
        states[label] = {}
        for row in rows:
            props = row['properties']
            if not isinstance(props, dict) or not isinstance(row['name'], str):
                raise ValueError('INVALID_ROW')
            status = props.get('Status') or 'UNKNOWN'
            if not isinstance(status, str):
                raise ValueError('INVALID_STATUS')
            states[label][status] = states[label].get(status, 0) + 1
    return {'status': 'SNAPSHOT_QA_PASS', 'input_sha256': actual,
            'input_bytes': len(raw), 'counts': counts, 'status_counts': states,
            'remote_writes': 0, 'model_training': 'NOT_RUN',
            'content_generation': 'NOT_RUN', 'production_ready': False,
            'limitation': 'Metadata QA only; evidence relations and attachments are not verified.'}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--sha256', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    report = inspect(args.input.read_bytes(), args.sha256)
    # A fresh output path is required; never overwrite input or an old receipt.
    args.output.mkdir(parents=True, exist_ok=False)
    report['interpreter'] = sys.version
    result = (json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + '\n').encode()
    (args.output / 'receipt.json').write_bytes(result)
    (args.output / 'sha256.json').write_text(json.dumps({'receipt.json': hashlib.sha256(result).hexdigest()}), encoding='utf-8')
    print(json.dumps({'status': report['status'], 'counts': report['counts'], 'remote_writes': 0}))

if __name__ == '__main__':
    main()
