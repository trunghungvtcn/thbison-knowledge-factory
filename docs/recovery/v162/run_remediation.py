"""Local-only V16.2 driver; all remote reads are supplied as saved inputs."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from kf_pilot.v162_remediation.core import BASELINE, compute, digest, require


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def lines(path):
    return [json.loads(x) for x in path.read_text(encoding='utf-8').splitlines() if x]


def verify_assets():
    archive = ROOT/'.kaggle-deploy/v161-no-write/package/v161-no-write.zip'
    with zipfile.ZipFile(archive) as z:
        manifest = json.loads(z.read('sha256_manifest.json'))
        for name, expected in manifest.items():
            require(hashlib.sha256(z.read(name)).hexdigest() == expected, 'approved ZIP manifest mismatch')
            if name.startswith(('src/', 'notebooks/', 'scripts/')):
                require((ROOT/name).read_bytes() == z.read(name), 'approved asset changed: '+name)
    pack = ROOT/'vendor/v162-deployment-pack'
    for row in (pack/'PACKAGE_SHA256SUMS.txt').read_text().splitlines():
        h, name = row.split(maxsplit=1)
        require(hashlib.sha256((pack/name.strip()).read_bytes()).hexdigest() == h, 'V162 pack hash mismatch')


def parse_live(raw):
    result = {}
    for response in raw:
        require(not response.get('isError'), 'live connector read failed')
        data = json.loads(response['content'][0]['text'])
        text = data['text']
        props = json.loads(re.search(r'<properties>\s*(.*?)\s*</properties>', text, re.S).group(1))
        pid = re.search(r'/p/([a-f0-9]{32})', data['url']).group(1)
        pid = f'{pid[:8]}-{pid[8:12]}-{pid[12:16]}-{pid[16:20]}-{pid[20:]}'
        parent = re.search(r'<parent-data-source url="collection://([a-f0-9-]+)"', text).group(1).replace('-', '')
        require(pid not in result, 'duplicate live page')
        result[pid] = {'parent': parent, 'properties': props, 'last_edited_at': data.get('page_last_edited_at')}
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--output', type=Path, required=True)
    ap.add_argument('--evidence', type=Path, help='Reviewed evidence bindings keyed by issue ID; never generated from plausible prose')
    args = ap.parse_args()
    require(not args.output.exists(), 'new output directory required')
    verify_assets()
    baseline_dir = ROOT/'v162/baseline-reproduced'
    plan = load(baseline_dir/'notion_typed_update_plan.json')
    require(digest(plan) == BASELINE, 'V162_BASELINE_RECONCILIATION_FAIL: hash')
    versions = lines(baseline_dir/'claim_versions.jsonl')
    issues = lines(baseline_dir/'migration_issues.jsonl')
    reviews = parse_live(load(ROOT/'v162/inputs/live_reviews_raw.json'))
    require(set(reviews) == {r['page_id'] for r in plan['operations']}, 'live review coverage mismatch')
    raw_schema = load(ROOT/'v162/inputs/schema_raw.json')
    schema_text = json.loads(raw_schema['content'][0]['text'])['text']
    state = json.loads(re.search(r'<data-source-state>\s*(.*?)\s*</data-source-state>', schema_text, re.S).group(1))
    schema = {k: 'rich_text' if v['type'] == 'text' else v['type'] for k, v in state['schema'].items()}
    # No scope-bound structured source literals have been supplied for these prose rows.
    # Empty evidence does NOT resolve blockers; relation URLs alone are not proof.
    evidence = load(args.evidence) if args.evidence else {}
    discovered_ids = {r['issue_id'] for r in __import__('kf_pilot.v162_remediation.core', fromlist=['inventory']).inventory(versions, issues)}
    require(isinstance(evidence, dict) and set(evidence) <= discovered_ids, 'unmatched evidence issue ID')
    result = compute(versions, issues, plan['operations'], reviews, schema, evidence)
    observed = result['v162_readiness_report.json']['issue_count_by_type']
    # Checkpoint expectations are audit gates, never a row generator.
    require(observed == {'OBJECT_VALUE_UNSTRUCTURED': 70, 'CONDITION_CONNECTIVE_AMBIGUOUS': 9},
            'V162_BASELINE_RECONCILIATION_FAIL: checkpoint issue counts')
    replay = compute(list(reversed(versions)), list(reversed(issues)), list(reversed(plan['operations'])), reviews, schema, evidence)
    require(result == replay, 'reverse replay differs')
    require(digest(load(baseline_dir/'notion_typed_update_plan.json')) == BASELINE, 'baseline changed after')
    verify_assets()
    readiness = result['v162_readiness_report.json']
    readiness.update(reverse_replay='PASS', approved_assets_match=True, live_review_count=len(reviews),
                     final_status='V162_REMEDIATION_PASS / PHASE_F_NOT_AUTHORIZED')
    result['v162_input_manifest.json'] = {
        str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest()
        for p in sorted(list((ROOT/'v162/inputs').glob('*.json')) + list(baseline_dir.glob('*')))
        if p.is_file()}
    if args.evidence:
        result['v162_input_manifest.json']['evidence_bindings'] = hashlib.sha256(args.evidence.read_bytes()).hexdigest()
    args.output.mkdir(parents=True)
    for name, value in result.items():
        with (args.output/name).open('x', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False)
            f.write('\n')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(args.output.glob('*.json'))}
    with (args.output/'artifact_hashes.json').open('x', encoding='utf-8') as f:
        json.dump(hashes, f, sort_keys=True, indent=2)
        f.write('\n')
    print(json.dumps(readiness, indent=2))


if __name__ == '__main__':
    main()
