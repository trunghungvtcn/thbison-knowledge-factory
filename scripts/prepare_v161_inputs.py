"""Adapt checksum-pinned V15 artifacts to V16.1; no network or credentials."""
import hashlib
import json
from pathlib import Path
from uuid import UUID
import pyarrow.parquet as pq

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / '.kaggle-deploy/release-20260904/claims-v15-output/kf-pilot-review-output'
OUT = ROOT / 'v16_migration/v161-inputs'
PINS = {
    'knowledge/canonical_knowledge.parquet': '74130d9861f46a00ad82b0870ab8cbbfa2f3a5a42be22687747559eb79f14f05',
    'review/notion_v2_sync.parquet': 'f11b2394e6609e6fb8bfda39e84e36ea8f7af00a576a6b1037f14c10a7f9e6c6',
}


def main():
    for name, expected in PINS.items():
        if hashlib.sha256((BASE / name).read_bytes()).hexdigest() != expected:
            raise ValueError('V15 baseline fingerprint changed: ' + name)
    canonical = pq.read_table(BASE / 'knowledge/canonical_knowledge.parquet').to_pylist()
    mappings = pq.read_table(BASE / 'review/notion_v2_sync.parquet').to_pylist()
    live_raw = json.loads((OUT / 'live_snapshot_raw.json').read_text(encoding='utf-8'))
    live = {r['Knowledge ID']: r for r in live_raw['results']}
    if len(live) != len(live_raw['results']):
        raise ValueError('duplicate live legacy ID')
    km = [r for r in mappings if r['target'] == 'KNOWLEDGE_ITEM']
    pages = {r['candidate_id']: r['notion_page_id'] for r in km}
    if len(canonical) != 70 or len(mappings) != 102 or len(km) != 70 or len(pages) != 70 or len(set(pages.values())) != 70:
        raise ValueError('baseline cardinality or mapping collision')
    rows, reviews = [], []
    for r in canonical:
        key = r['knowledge_id']
        current = live[key]
        page = pages[key]
        if UUID(current['url'].rstrip('/').split('/')[-1]) != UUID(page):
            raise ValueError('live page mapping changed')
        rows.append(dict(legacy_canonical_id=key, canonical_text=r['canonical_text'],
            product_family=r['subject_product_family'], subject=r['subject_product_family'],
            predicate=r['predicate'], object_value=r['canonical_text'],
            jurisdiction=r['jurisdiction'], applicability=r['applicability_scope'],
            legal_status=r['legal_status'], condition_tags=json.loads(r['conditions_json']),
            system_status=r['decision_state'], notion_page_id=page))
        reviews.append(dict(page_id=page, legacy_id=key, decision=current['Decision'] or 'PENDING',
            reviewer_note=current['Reviewer Note'], status=current['Status'],
            reviewed_entity_id=None, reviewed_version_id=None))
    for filename, data in [('v15_canonical_rows.json', rows), ('live_knowledge_snapshot.json', reviews),
                           ('v15_all_page_mappings.json', mappings)]:
        (OUT / filename).write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    manifest = {'baseline_pins': PINS, 'snapshot_captured_at': live_raw['captured_at'],
        'files': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.json') if p.name != 'input_manifest.json'},
        'canonical_rows': len(rows), 'live_review_rows': len(reviews), 'all_page_mappings': len(mappings),
        'object_value_policy': 'Retain legacy prose and block; do not infer structured semantic values.'}
    (OUT / 'input_manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')
    print(json.dumps({'rows':len(rows),'review_snapshots':len(reviews),'mappings':len(mappings)}))


if __name__ == '__main__':
    main()
