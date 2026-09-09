"""Discover/freeze/extract/critic/route/index/preview; all writes confined to local state."""
import argparse
import html
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit

from kf_pilot.v166_evidence_completion.canonical import confined, digest, load, require, rows, sha256
from kf_pilot.v166_evidence_completion.pipeline import BASELINE
from .policy import POLICY_HASH, POLICY_ID, candidates, decide, retrieve
from .storage import Budget, Store, atomic, lock
from .transport import fetch

ROOT = Path(__file__).resolve().parents[3]
LEGACY = {
    'baseline': 'v162/baseline-reproduced/notion_typed_update_plan.json',
    'mapping': 'v164/artifacts/final-003/v164_mapping_snapshot.jsonl',
    'human': 'v164/artifacts/final-003/v164_human_audit_snapshot.jsonl',
    'ledger': 'v165/artifacts/final-001/projected_issue_ledger.json',
    'original_issues': 'v163/artifacts/final-002/v162_issue_ledger.json',
    'blockers': 'v165/artifacts/final-001/new_blockers.jsonl',
    'proposals': 'v165/artifacts/final-001/complete_record_proposals.jsonl',
    'records': 'v165/artifacts/final-001/projected_record_plan.json',
    'aliases': 'v162/baseline-reproduced/claim_aliases.jsonl',
}


def invariant():
    paths = {k: ROOT / v for k, v in LEGACY.items()}
    require(digest(load(paths['baseline'])) == BASELINE, 'PRODUCTION_BASELINE_CHANGED')
    mappings = rows(paths['mapping']); ledger = load(paths['ledger'])['issues']
    original = load(paths['original_issues'])['issues']; blockers = rows(paths['blockers'])
    require(len(mappings) == 70 and len({x['page_id'] for x in mappings}) == 70, 'MAPPING_CHANGED')
    require({x['issue_id'] for x in ledger} == {x['issue_id'] for x in original + blockers}, 'ISSUE_SET_CHANGED')
    require(len(ledger) == len({x['issue_id'] for x in ledger}) == 85, 'ISSUE_UNIVERSE')
    return {'baseline': BASELINE, 'mappings': len(mappings), 'issues': len(ledger),
            'open_issues': sum(x['resolution_status'] != 'RESOLVED' for x in ledger),
            'files': {k: sha256(p.read_bytes()) for k, p in paths.items()},
            'issue_ids_hash': digest(sorted(x['issue_id'] for x in ledger))}


def code_hash():
    paths = list(Path(__file__).parent.glob('*.py'))
    paths += [ROOT / 'src/kf_pilot/v166_evidence_completion/canonical.py',
              ROOT / 'src/kf_pilot/v166_evidence_completion/schemas.py',
              ROOT / 'src/kf_pilot/v16/identity.py']
    return digest({p.relative_to(ROOT).as_posix(): sha256(p.read_bytes()) for p in paths})


def legacy_records():
    plans = load(ROOT / LEGACY['records'])['records']
    versions = rows(ROOT / 'v162/baseline-reproduced/claim_versions.jsonl')
    by_version = {r['claim_version_id']: r for r in versions}
    aliases = rows(ROOT / LEGACY['aliases'])
    result = []
    for plan in plans:
        old = by_version.get(plan['base_version_id'])
        require(old and old['claim_entity_id'] == plan['entity_id'], 'LEGACY_VERSION_JOIN')
        record = dict(plan, semantic_payload=old['semantic_payload'], source_system_status=old['source_system_status'])
        record['aliases'] = [value for a in aliases if a['claim_entity_id'] == plan['entity_id']
                             for value in (a['alias_key'], a['alias_value'])]
        result.append(record)
    require(len(result) == 70, 'LEGACY_LINEAGE_COUNT')
    return result


def validate_config(c):
    require(set(c) == {'schema_version', 'mode', 'as_of', 'legal_as_of', 'parent_revision',
                       'temporal_delta', 'topic', 'production_authorized', 'sources'}, 'CONFIG_KEYS')
    require(type(c['schema_version']) is int and c['schema_version'] == 1
            and c['mode'] == 'LOCAL_SHADOW' and c['production_authorized'] is False, 'LOCAL_ONLY')
    from kf_pilot.v166_evidence_completion.schemas import iso_time
    iso_time(c['as_of']); iso_time(c['legal_as_of'])
    require(c['legal_as_of'] == '2026-09-05T00:00:00+07:00', 'LEGACY_TIME_CHANGED')
    require(type(c['sources']) is list and 0 < len(c['sources']) <= 40, 'SOURCE_COUNT')
    require(len({s['source_id'] for s in c['sources']}) == len(c['sources']), 'DUPLICATE_SOURCE')
    for s in c['sources']:
        require(set(s) == {'source_id', 'url', 'publisher', 'provenance_family', 'authority', 'access', 'scope', 'subtopic'}, 'SOURCE_KEYS')
        require(s['access'] == 'PUBLIC' and urlsplit(s['url']).scheme == 'https', 'SOURCE_ACCESS')
    return c


def acquire(config, root):
    config = validate_config(config)
    root = Path(root); store = Store(root / 'checkpoint'); budget = Budget(store)
    manifest_path = root / 'acquisition.json'
    # Completed acquisition is immutable; restart reuses exact bytes and counters.
    with lock(root / 'acquisition.lock'):
        manifest = load(manifest_path) if manifest_path.exists() else {'config_hash': digest(config), 'sources': []}
        require(manifest['config_hash'] == digest(config), 'ACQUISITION_CONFIG_CHANGED')
        done = {s['source_id'] for s in manifest['sources']}
        for spec in config['sources']:
            if spec['source_id'] in done:
                continue
            entry = dict(spec, status='ACCESS_BLOCKED', error=None)
            try:
                response, raw = fetch(spec['url'], budget=budget)
                require(urlsplit(response.geturl()).hostname == urlsplit(spec['url']).hostname, 'PUBLISHER_REDIRECT_MISMATCH')
                require(response.headers.get_content_type() in {'text/html', 'application/pdf'}, 'SOURCE_MIME')
                h = sha256(raw); dest = root / 'raw' / (h + '.bin')
                dest.parent.mkdir(parents=True, exist_ok=True)
                if dest.exists():
                    require(sha256(dest.read_bytes()) == h, 'RAW_CACHE_TAMPER')
                else:
                    with dest.open('xb') as f:
                        f.write(raw)
                        f.flush()
                        import os
                        os.fsync(f.fileno())
                entry.update(status='FETCHED', raw_sha256=h, bytes=len(raw), raw_path='raw/' + dest.name,
                             final_url=response.geturl(), fetched_at=response.fetched_at,
                             mime=response.headers.get_content_type(), http_status=response.status)
            except Exception as exc:
                entry['error'] = type(exc).__name__ + ':' + str(exc)[:180]
            manifest['sources'].append(entry)
            atomic(manifest_path, manifest)
        atomic(root / 'budget.json', budget.snapshot())
    return manifest


def frozen(config, manifest):
    spec = {'schema_version': 1, 'source_revisions': sorted(s['raw_sha256'] for s in manifest['sources'] if s['status'] == 'FETCHED'),
            'as_of': config['as_of'], 'legal_as_of': config['legal_as_of'],
            'parent_revision': config['parent_revision'], 'temporal_delta': config['temporal_delta']}
    return dict(spec, corpus_revision=digest(spec))


def generate(config, acquisition, input_root, legacy_records):
    corpus = frozen(config, acquisition); rev = corpus['corpus_revision']
    records = []
    for source in acquisition['sources']:
        if source['status'] != 'FETCHED' or source['mime'] != 'text/html':
            continue
        raw = confined(input_root, source['raw_path']).read_bytes()
        require(sha256(raw) == source['raw_sha256'], 'SOURCE_TAMPER')
        for claim in candidates(raw, source, rev, config['as_of']):
            decision = decide(claim, source, raw, rev, config['as_of'], legacy_records)
            records.append({'claim': claim, 'decision': decision})
    # Any competing values within the same source-scoped predicate are retained for review.
    groups = {}
    for r in records:
        c = r['claim']; groups.setdefault(digest([c['scope'], c['predicate']]), set()).add(c['value']['value'])
    for r in records:
        c = r['claim']
        # drive_components is explicitly a set-valued description, housing material is singular.
        if c['predicate'] == 'housing_material' and len(groups[digest([c['scope'], c['predicate']])]) > 1:
            r['decision'].update(state='REVIEW_EXCEPTION', reasons=['CORPUS_CONFLICT'], allowed_uses=[])
    queue = []
    for p in rows(ROOT / LEGACY['proposals']):
        queue.append({'entity_id': p['entity_id'], 'base_version_id': p['base_version_id'],
                      'proposal_hash': p.get('proposal_hash') or digest(p), 'risk': 'R3', 'state': 'REVIEW_EXCEPTION',
                      'reason': 'LEGACY_CONDITIONS_EXCEPTIONS_LEGAL_TIME_UNRESOLVED',
                      'legacy_ids': [p['entity_id']], 'authorized_to_execute': False})
    queue += [{'entity_id': r['claim']['entity_id'], 'risk': r['decision']['risk'],
               'state': r['decision']['state'], 'reasons': r['decision']['reasons']} for r in records
              if r['decision']['state'] != 'MACHINE_ACCEPTED']
    return {'corpus': corpus, 'records': records, 'exception_queue': queue,
            'authorized_to_execute': False, 'policy_hash': POLICY_HASH}


def preview(result, acquisition):
    sources = {s['source_id']: s for s in acquisition['sources']}
    items, seen = [], set()
    for r in result['records']:
        c = r['claim']
        eligible = retrieve([r], 'DESCRIPTIVE_DRAFT', c['scope'], c['as_of'], result['corpus']['corpus_revision'])
        if not eligible or c['entity_id'] in seen:
            continue
        seen.add(c['entity_id']); source = sources[c['evidence']['source_id']]
        items.append({'entity_id': c['entity_id'], 'manufacturer': c['scope']['manufacturer'],
                      'model': c['scope']['model'], 'text': c['evidence']['quote'], 'use': 'DESCRIPTIVE_DRAFT',
                      'source_url': source['final_url'], 'raw_sha256': c['evidence']['raw_sha256'],
                      'start': c['evidence']['start'], 'end': c['evidence']['end'], 'claim_hash': digest(c)})
    return {'status': 'LOCAL_DRAFT_NOT_PUBLISHED', 'items': items}


def read_current(config_path, root):
    """Trusted consumer entrypoint. Do not serve committed JSON without this check."""
    root = Path(root); config = validate_config(load(config_path))
    info = load(root / 'run.json'); pins = info['pins']
    acquisition = load(root / 'acquisition.json')
    require(pins['code'] == code_hash() and pins['policy'] == POLICY_HASH, 'STALE_CODE_OR_POLICY')
    require(pins['config'] == digest(config) and pins['acquisition'] == digest(acquisition), 'STALE_INPUT')
    require(pins['legacy'] == digest(invariant()), 'STALE_LEGACY')
    result = Store(root / 'checkpoint').visible(info['task_key'], pins)
    require(result is not None, 'REVOKED_OR_UNCOMMITTED')
    legacy = legacy_records()
    require(pins['lineage'] == digest(legacy), 'STALE_LINEAGE')
    require(generate(config, acquisition, root, legacy) == result, 'INDEPENDENT_RECOMPUTE_FAILED')
    draft = preview(result, acquisition)
    require(load(root / 'preview.json') == draft, 'PREVIEW_TAMPER')
    return result, draft


def invalidate(root, dependency):
    """Remove dependent local materialized drafts; unrelated runs remain available."""
    root = Path(root); store = Store(root / 'checkpoint')
    store.revoke(dependency)
    info = load(root / 'run.json')
    if dependency in info['pins'].values():
        atomic(root / 'preview.json', {'status': 'REVOKED', 'items': []})
        (root / 'preview.html').write_text('<!doctype html><meta charset="utf-8"><h1>REVOKED</h1><p>Evidence or policy is no longer eligible.</p>', encoding='utf-8')
    return {'dependency': dependency, 'state': 'REVOKED', 'production_write': False}


def run(config_path, output, online=False):
    config = validate_config(load(config_path)); root = Path(output); root.mkdir(parents=True, exist_ok=True)
    before = invariant()
    initial = root / 'invariants-before.json'
    if initial.exists():
        require(load(initial) == before, 'LEGACY_INPUT_CHANGED')
    else:
        atomic(initial, before)
    if online:
        acquisition = acquire(config, root)
    else:
        acquisition = load(root / 'acquisition.json')
    require(acquisition['config_hash'] == digest(config), 'CONFIG_PIN')
    legacy = legacy_records()
    pins = {'config': digest(config), 'code': code_hash(), 'policy': POLICY_HASH,
            'corpus': frozen(config, acquisition)['corpus_revision'], 'legacy': digest(before),
            'acquisition': digest(acquisition), 'lineage': digest(legacy), 'model': 'NOT_RUN'}
    pins.update({'source:' + s['source_id']: s['raw_sha256'] for s in acquisition['sources'] if s['status'] == 'FETCHED'})
    key = digest(pins); store = Store(root / 'checkpoint')
    result, replay = store.commit(key, pins, lambda: generate(config, acquisition, root, legacy))
    require(store.visible(key, pins) is not None, 'STALE_RUN')
    expected = generate(config, load(root / 'acquisition.json'), root, legacy)
    require(expected == result, 'INDEPENDENT_RECOMPUTE_FAILED')
    draft = preview(result, acquisition)
    atomic(root / 'preview.json', draft)
    page = '<!doctype html><meta charset="utf-8"><title>Knowledge Factory – local preview</title>'
    page += '<style>body{font:16px system-ui;max-width:960px;margin:40px auto;line-height:1.6}article{padding:20px;border:1px solid #ccd;margin:14px 0}small{color:#556}</style>'
    page += '<h1>Pa lăng xích kéo tay — knowledge có nguồn</h1><p>Bản nháp local. Phạm vi mô tả cấu tạo của đúng hãng/model; chưa phải khuyến nghị sử dụng.</p>'
    for item in draft['items']:
        page += '<article><h2>' + html.escape(item['manufacturer'] + ' / ' + item['model']) + '</h2>'
        page += '<p>' + html.escape(item['text']) + '</p><a href="' + html.escape(item['source_url'], quote=True) + '">Nguồn OEM</a>'
        page += '<br><small>Claim ' + item['claim_hash'][:16] + ' · source ' + item['raw_sha256'][:16] + '</small></article>'
    (root / 'preview.html').write_text(page, encoding='utf-8')
    after = invariant(); require(before == after, 'LEGACY_MUTATION')
    atomic(root / 'invariants-after.json', after)
    states = Counter(r['decision']['state'] for r in result['records'])
    metrics = {'documents_attempted': len(acquisition['sources']),
               'documents_fetched': sum(s['status'] == 'FETCHED' for s in acquisition['sources']),
               'unique_documents': len(set(result['corpus']['source_revisions'])),
               'provenance_families': len({s['provenance_family'] for s in acquisition['sources'] if s['status'] == 'FETCHED'}),
               'claims': len(result['records']), 'claims_by_state': dict(states), 'preview_items': len(draft['items']),
               'exception_queue': len(result['exception_queue']), 'legacy_open_issues': before['open_issues'],
               'abstention_rate': (1 - states['MACHINE_ACCEPTED'] / len(result['records'])) if result['records'] else None,
               'model_calls': None, 'model_calls_status': 'NOT_RUN', 'cost': None, 'cost_status': 'UNKNOWN',
               'ocr': 'NOT_RUN', 'production': 'NOT_DEPLOYED', 'legacy_mutations': 0,
               'budget': Budget(store).snapshot(), 'source_coverage': dict(Counter(s['subtopic'] for s in acquisition['sources'] if s['status'] == 'FETCHED'))}
    metrics.update(claims_by_risk=dict(Counter(r['decision']['risk'] for r in result['records'])),
                   allowed_use_counts=dict(Counter(u for r in result['records'] for u in r['decision']['allowed_uses'])),
                   citation_verified=len(result['records']), citation_failed=0,
                   useful_scope_predicate_coverage=len({digest([r['claim']['scope'], r['claim']['predicate']]) for r in result['records'] if r['decision']['state'] == 'MACHINE_ACCEPTED'}),
                   human_field_mutations=0, mapping_mutations=0,
                   enrichment_rounds=sum(g['rounds'] for g in store.transact(lambda s:s['gaps']).values()),
                   oldest_queue_age_seconds=None, oldest_queue_age_status='NOT_MEASURED_LEGACY_CREATED_AT_UNAVAILABLE',
                   queue_risk_counts=dict(Counter(r['risk'] for r in result['exception_queue'])))
    atomic(root / 'data_quality_metrics.json', metrics)
    info = {'task_key': key, 'pins': pins, 'replay': replay, 'verifier': 'CURRENT_PASS',
            'machine_lane': 'MACHINE_LANE_WORKING' if draft['items'] else 'NO_ELIGIBLE_CONTENT',
            'production': 'NOT_DEPLOYED', 'authorized_to_execute': False}
    atomic(root / ('replay.json' if replay else 'run.json'), info)
    return info


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--config', required=True); p.add_argument('--output', required=True)
    p.add_argument('--online', action='store_true')
    args = p.parse_args()
    print(run(args.config, args.output, args.online))


if __name__ == '__main__':
    main()
