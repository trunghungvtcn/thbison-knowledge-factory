from __future__ import annotations

from copy import deepcopy
import hashlib
import json
import os
from pathlib import Path
from uuid import UUID

from kf_pilot.v16.condition_ast import canonicalize_ast, contains_unresolved
from kf_pilot.v16.object_value import normalize_object_value

PRODUCTION_IDS = frozenset(x.replace('-', '') for x in (
    '87318868-8be2-4e27-8ab6-7a3d0b53bb32', 'a4812f47-e1a6-4aa1-a619-558a79a4c4ff',
    '9d53865d-0cdd-41f3-a6c6-5d171b4e50f4', '0cd6447eb7ff47d4bee55126660eef19',
    '8d84f24e72ef48bd889ee1f0a2ddb630', '30a97a9809cb4ef9985ffc0b0b1f6384',
    '755f1fbb6c0b463f9ef26e54e6fa216e', '3cefbe3f22e681479dbbe30469cc7877'))
FIELDS = {'Claim Text': 'rich_text', 'Run ID': 'rich_text', 'Condition Status': 'select', 'System Status': 'select'}
HUMAN = frozenset({'Decision', 'Reviewer Note', 'Reviewed Entity ID', 'Reviewed Version ID',
    'Reviewer', 'Review Notes', 'Editorial Notes', 'Approval Timestamp', 'Manual Tags'})


class Blocked(ValueError):
    pass


def ident(value):
    try:
        return UUID(str(value)).hex
    except (ValueError, TypeError, AttributeError):
        raise Blocked('missing or invalid staging UUID') from None


def canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(',', ':'), allow_nan=False)


def writable(prop, kind):
    """Strip only API metadata; retain all writable rich-text styling/links."""
    if prop.get('type', kind) != kind:
        raise Blocked('property type mismatch')
    if kind == 'select':
        selected = prop.get('select')
        return {'select': None if selected is None else {'name': selected['name']}}
    parts = []
    for item in prop.get('rich_text', []):
        if item.get('type', 'text') != 'text':
            raise Blocked('unsupported before-image rich-text node')
        part = {'type': 'text', 'text': {'content': item['text']['content']}}
        if item['text'].get('link') is not None:
            part['text']['link'] = item['text']['link']
        annotations = {k: v for k, v in item.get('annotations', {}).items() if v not in (False, 'default')}
        if annotations:
            part['annotations'] = annotations
        parts.append(part)
    return {'rich_text': parts}


def validate_properties(properties):
    if not properties or set(properties) - set(FIELDS):
        raise Blocked('unknown or human-owned property')
    for name, value in properties.items():
        kind = FIELDS[name]
        if set(value) != {kind} or writable(value, kind) != value:
            raise Blocked('invalid typed property')
        if kind == 'rich_text' and any(len(x['text']['content']) > 2000 for x in value[kind]):
            raise Blocked('rich text too long')


def validate_plan(plan, environment, target_id, page_ids, denied=()):
    deny = PRODUCTION_IDS | {ident(x) for x in denied}
    if environment != 'STAGING':
        raise Blocked('V161_ENV must be STAGING')
    target = ident(target_id)
    if target in deny:
        raise Blocked('production target denied')
    if set(plan) != {'target_kind', 'records'} or plan['target_kind'] != 'DEDICATED_STAGING':
        raise Blocked('schema/SQL/scheduler/unknown routes forbidden')
    records = plan['records']
    if not isinstance(records, list) or not 1 <= len(records) <= 3 or len(page_ids) != len(records):
        raise Blocked('plan/page count must match and be 1..3')
    ids = [ident(x) for x in page_ids]
    if len(set(ids)) != len(ids) or any(x in deny or x == target for x in ids):
        raise Blocked('duplicate or production page denied')
    seen = set()
    for index, record in enumerate(records, 1):
        if set(record) != {'operation', 'environment', 'synthetic', 'synthetic_id', 'target_ref', 'properties', 'semantic_fixture'}:
            raise Blocked('unknown operation fields')
        if record['operation'] != 'UPDATE' or record['environment'] != 'STAGING' or record['synthetic'] is not True:
            raise Blocked('synthetic STAGING UPDATE only')
        sid = record['synthetic_id']
        if sid != f'V161-STAGING-SYNTH-{index:03d}' or sid in seen:
            raise Blocked('synthetic ID mismatch')
        seen.add(sid)
        if record['target_ref'] != f'STAGING_FIXTURE_PAGE_{index:03d}':
            raise Blocked('fixture page reference mismatch')
        if set(record['properties']) != set(FIELDS):
            raise Blocked('fixture must use exactly the system allowlist')
        validate_properties(record['properties'])
        semantic = record['semantic_fixture']
        if set(semantic) != {'object_value', 'condition_ast'}:
            raise Blocked('unknown semantic fields')
        _, issues = normalize_object_value(semantic['object_value'])
        if issues or contains_unresolved(semantic['condition_ast']) or canonicalize_ast(semantic['condition_ast']) != {'op': 'TRUE'}:
            raise Blocked('structured, resolved synthetic records required')
    return target, ids


def dump(path, value):
    with path.open('x', encoding='utf-8') as stream:
        stream.write(json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False) + '\n')
        stream.flush()
        os.fsync(stream.fileno())


class GuardedAdapter:
    def __init__(self, transport, plan, environment, target_id, page_ids, denied=()):
        self.plan = deepcopy(plan)
        self.environment = environment
        self.denied = tuple(denied)
        self.target, self.ids = validate_plan(plan, environment, target_id, page_ids, denied)
        self.transport = transport
        self.before = {}
        self.patch_count = 0

    def preflight(self):
        validate_plan(self.plan, self.environment, self.target, self.ids, self.denied)
        schema = self.transport.read_schema(self.target)
        for name, kind in FIELDS.items():
            if schema.get(name, {}).get('type') != kind:
                raise Blocked('staging schema missing/type mismatch; no schema mutation allowed')
        for record, page in zip(self.plan['records'], self.ids):
            value = self.read(page)
            if value['marker'] != record['synthetic_id']:
                raise Blocked('existing staging page marker mismatch')
            for name, kind in FIELDS.items():
                if kind == 'select':
                    intended = record['properties'][name]['select']['name']
                    original = value['properties'][name]['select']
                    required = {intended} | ({original['name']} if original else set())
                    if not required <= set(schema[name]['options']):
                        raise Blocked('missing select option; implicit schema expansion forbidden')

    def read(self, page):
        if page not in self.ids:
            raise Blocked('page outside fixed staging plan')
        raw = self.transport.read_page(page)
        if ident(raw['target_id']) != self.target or raw.get('archived'):
            raise Blocked('page is outside staging target or archived')
        if raw['marker'] != self.plan['records'][self.ids.index(page)]['synthetic_id']:
            raise Blocked('synthetic page marker changed')
        return {'page_id': page, 'target_id': self.target, 'marker': raw['marker'],
            'properties': {name: writable(raw['properties'][name], kind) for name, kind in FIELDS.items()},
            'human_properties': deepcopy({k: v for k, v in raw['properties'].items() if k in HUMAN})}

    def write(self, page, desired, expected, *, rollback=False):
        validate_plan(self.plan, self.environment, self.target, self.ids, self.denied)
        validate_properties(desired)
        if page not in self.before:
            raise Blocked('before-image required')
        index = self.ids.index(page)
        authorized = self.before[page]['properties'] if rollback else self.plan['records'][index]['properties']
        if desired != authorized:
            raise Blocked('properties outside prepared apply/rollback plan')
        current = self.read(page)
        if current['properties'] != expected:
            raise Blocked('concurrent system-property change; stop without overwrite')
        if current['properties'] != desired:
            self.transport.patch_page(page, desired)
            self.patch_count += 1
            return 1
        return 0


def run_cycle(adapter, output):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    adapter.preflight()
    before = {page: adapter.read(page) for page in adapter.ids}
    rollback = [{'operation': 'UPDATE', 'page_id': p, 'properties': v['properties']} for p, v in before.items()]
    dump(output/'staging_plan.json', adapter.plan)
    dump(output/'staging_before.json', before)
    dump(output/'staging_rollback_plan.json', rollback)
    # All snapshots and recovery artifacts must be durable before first PATCH.
    adapter.before = deepcopy(before)
    if hasattr(adapter.transport, 'arm_from_snapshot'):
        adapter.transport.arm_from_snapshot(output)
    attempted = []
    success = False
    rollback_ok = True
    try:
        count = 0
        for record, page in zip(adapter.plan['records'], adapter.ids):
            attempted.append(page)  # Includes ambiguous transport failures.
            count += adapter.write(page, record['properties'], before[page]['properties'])
        readback = {p: adapter.read(p) for p in adapter.ids}
        for record, page in zip(adapter.plan['records'], adapter.ids):
            if readback[page]['properties'] != record['properties']:
                raise Blocked('apply readback mismatch')
            if readback[page]['human_properties'] != before[page]['human_properties']:
                raise Blocked('human-field drift detected')
        dump(output/'staging_readback.json', readback)
        second_delta = sum(adapter.write(p, r['properties'], r['properties']) for r, p in zip(adapter.plan['records'], adapter.ids))
        second = {p: adapter.read(p) for p in adapter.ids}
        if second != readback or second_delta:
            raise Blocked('idempotency failed')
        dump(output/'staging_apply_report.json', {'status': 'PASS', 'first_pass_updates': count,
            'second_pass_semantic_delta': second_delta, 'second_pass_updates': 0,
            'human_field_writes': 0, 'production_writes': 0, 'creates': 0, 'schema_mutations': 0,
            'sql': 0, 'scheduler': 0, 'transport': adapter.transport.mode})
        success = True
    finally:
        restored = {}
        conflicts = []
        for page in reversed(attempted):
            try:
                current = adapter.read(page)
                intended = adapter.plan['records'][adapter.ids.index(page)]['properties']
                if current['properties'] not in (before[page]['properties'], intended):
                    raise Blocked('rollback conflict requires manual recovery')
                adapter.write(page, before[page]['properties'], current['properties'], rollback=True)
            except Exception:
                conflicts.append(page)
        for page in adapter.ids:
            try:
                restored[page] = adapter.read(page)
                if restored[page]['properties'] != before[page]['properties']:
                    rollback_ok = False
            except Exception:
                rollback_ok = False
        rollback_ok = rollback_ok and not conflicts
        dump(output/'staging_rollback_report.json', {'status': 'PASS' if rollback_ok else 'FAILED',
            'conflict_pages': conflicts, 'readback': restored, 'before_properties_equal': rollback_ok,
            'transport': adapter.transport.mode})
        if not success and not (output/'staging_apply_report.json').exists():
            dump(output/'staging_apply_report.json', {'status': 'FAILED', 'rollback_verified': rollback_ok,
                'transport': adapter.transport.mode})
    if not rollback_ok:
        raise Blocked('rollback verification failed; see recovery artifacts')
    hashes = {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.glob('*.json'))}
    dump(output/'artifact_hashes.json', hashes)
    return {'status': 'LOCAL_STAGING_HARNESS_PASS' if adapter.transport.mode == 'MEMORY' else 'REMOTE_STAGING_PASS',
        'remote_status': 'REMOTE_STAGING_NOT_RUN' if adapter.transport.mode == 'MEMORY' else 'REMOTE_STAGING_PASS',
        'updates': count, 'second_pass_semantic_delta': second_delta, 'rollback': 'PASS', 'artifact_hashes': hashes}
