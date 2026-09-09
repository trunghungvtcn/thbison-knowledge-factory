from copy import deepcopy
from collections import Counter
import hashlib
import json
import re

from kf_pilot.v16.object_value import normalize_object_value
from kf_pilot.v16.condition_ast import canonicalize_ast, contains_unresolved
from kf_pilot.v16.identity import claim_version_id

BASELINE = 'af9e6eac67a8debf022b9567806022c5e5477c837f876d1e95c280f421b4e399'
PARENT = '9d53865d0cdd41f3a6c65d171b4e50f4'
TYPES = {'OBJECT_VALUE_UNSTRUCTURED', 'CONDITION_CONNECTIVE_AMBIGUOUS'}
HUMAN = {'Decision', 'Reviewer Note', 'Reviewed Entity ID', 'Reviewed Version ID', 'Reviewer', 'Review Notes', 'Editorial Notes', 'Approval Timestamp', 'Manual Tags'}
SYSTEM = {'Object Value', 'Condition AST', 'Claim Entity ID', 'Claim Version ID'}


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def require(test, message):
    if not test:
        raise ValueError(message)


def inventory(versions, source_issues):
    """Recompute from semantic values and reconcile independently with migration issues."""
    result = []
    require(len({v['claim_entity_id'] for v in versions}) == len(versions), 'duplicate entity')
    for v in versions:
        values = []
        p = v['semantic_payload']
        if p['object_value'].get('type') == 'legacy_text':
            values.append(('OBJECT_VALUE_UNSTRUCTURED', p['object_value']['value']))
        if contains_unresolved(p['condition_ast']):
            values.append(('CONDITION_CONNECTIVE_AMBIGUOUS', p['condition_ast']))
        for typ, value in values:
            key = [v['claim_entity_id'], v['claim_version_id'], typ]
            result.append(dict(issue_id='ri_'+digest(key), entity_id=key[0], version_id=key[1],
                               issue_type=typ, source_text=value if isinstance(value, str) else canonical(value),
                               before_value=value, before_value_hash=digest(value)))
    rename = {'CONDITION_CONNECTIVE_UNRESOLVED': 'CONDITION_CONNECTIVE_AMBIGUOUS'}
    actual = Counter((r['entity_id'], r['issue_type']) for r in result)
    expected = Counter((r['claim_entity_id'], rename.get(r['code'], r['code'])) for r in source_issues)
    require(actual == expected, 'V162_BASELINE_RECONCILIATION_FAIL: issue inventory differs')
    return sorted(result, key=lambda r: r['issue_id'])


def resolve(issue, evidence):
    """Only a whole evidence literal, explicitly bound to entity/version/field, is eligible.

    Prose, extracted fragments, unreviewed evidence and unproven scope never resolve.
    No unit extraction from prose or connective inference from legacy tag lists.
    """
    if not evidence:
        return None
    field = 'object_value' if issue['issue_type'] == 'OBJECT_VALUE_UNSTRUCTURED' else 'condition_ast'
    needed = {'entity_id', 'version_id', 'field', 'ref', 'content', 'content_sha256', 'literal', 'scope_verified', 'authoritative'}
    if not needed <= evidence.keys():
        return None
    if (evidence['entity_id'], evidence['version_id'], evidence['field']) != (issue['entity_id'], issue['version_id'], field):
        return None
    if evidence['scope_verified'] is not True or evidence['authoritative'] is not True or not evidence['ref']:
        return None
    literal = evidence['literal']
    if evidence['content_sha256'] != hashlib.sha256(evidence['content'].encode()).hexdigest() or literal != evidence['content'].strip():
        return None
    try:
        if field == 'condition_ast':
            ast = canonicalize_ast(json.loads(literal))
            if contains_unresolved(ast):
                return None
            return {'condition_ast': ast, 'resolution_rule': 'EXPLICIT_WHOLE_AST_V1', 'after_value_hash': digest(ast)}
        # Literal must equal the whole original object, never a guessed excerpt.
        if literal != issue['source_text'].strip():
            return None
        if re.fullmatch(r'-?\d+(?:\.\d+)? [A-Za-z]+', literal):
            amount, unit = literal.split(' ')
            value = {'type': 'quantity', 'amount': amount, 'unit': unit}
            rule = 'EXACT_QUANTITY_LITERAL_V1'
        elif literal in ('true', 'false'):
            value = {'type': 'boolean', 'value': literal == 'true'}
            rule = 'EXACT_BOOLEAN_LITERAL_V1'
        elif literal in evidence.get('controlled_vocabulary', []):
            # Vocabulary must itself be supplied with an auditable authoritative binding.
            if not evidence.get('vocabulary_ref') or evidence.get('vocabulary_sha256') != digest(evidence['controlled_vocabulary']):
                return None
            value = {'type': 'enum', 'value': literal}
            rule = 'EXACT_CONTROLLED_ENUM_V1'
        else:
            value = json.loads(literal)
            rule = 'EXACT_STRUCTURED_LITERAL_V1'
        normalized, issues = normalize_object_value(value)
        if issues:
            return None
        return {'structured_value': normalized, 'resolution_rule': rule, 'after_value_hash': digest(normalized)}
    except (ValueError, TypeError, KeyError):
        return None


def ledger_for(issues, reviews, pages, evidence):
    ledger = []
    for issue in issues:
        r = deepcopy(issue)
        page = pages.get(r['entity_id'])
        review = reviews.get(page, {})
        decision = review.get('properties', {}).get('Decision')
        status = review.get('properties', {}).get('Status')
        r.update(page_id=page, decision_snapshot=decision,
                 reviewer_note_snapshot=review.get('properties', {}).get('Reviewer Note'),
                 source_evidence_refs=sorted(review.get('properties', {}).get('Evidence Sources', [])))
        e = evidence.get(r['issue_id'])
        resolved = resolve(r, e)
        if resolved:
            r.update(resolved, resolution_status='RESOLVED', source_evidence_refs=[e['ref']])
        else:
            r.update(resolution_status='HOLD' if decision in ('HOLD', 'REJECTED') or status in ('HOLD', 'REJECTED') else 'NEEDS_REVIEW',
                     review_reason='No authoritative, scope-bound whole typed literal/AST; preserve original semantics for human review.')
        ledger.append(r)
    return sorted(ledger, key=lambda r: r['issue_id'])


def gate_ledger(ledger, issues, reviews, pages, evidence):
    require(len({r['issue_id'] for r in ledger}) == len(ledger), 'duplicate issue ID')
    require(len({(r['entity_id'], r['version_id'], r['issue_type']) for r in ledger}) == len(ledger), 'duplicate issue key')
    # Replay derives every hash, decision binding and resolution; mere labels cannot pass.
    require(sorted(ledger, key=lambda r: r['issue_id']) == ledger_for(issues, reviews, pages, evidence),
            'ledger accounting/evidence/deterministic rule mismatch')


def plan_records(versions, operations, ledger, reviews, schema):
    mapped = {r['claim_entity_id']: r for r in operations}
    require(len(mapped) == len(operations), 'duplicate operation entity')
    counts = Counter(r.get('page_id') for r in operations)
    records = []
    for v in sorted(versions, key=lambda v: v['claim_entity_id']):
        entity = v['claim_entity_id']; op = mapped.get(entity, {})
        require(not op or op.get('operation') == 'UPDATE', 'CREATE forbidden')
        require(not (set(op.get('typed_properties', {})) & HUMAN), 'human-field payload forbidden')
        page = op.get('page_id'); review = reviews.get(page, {})
        props = review.get('properties', {})
        related = [r for r in ledger if r['entity_id'] == entity]
        payload = deepcopy(v['semantic_payload'])
        for issue in related:
            if issue['resolution_status'] == 'RESOLVED':
                field = 'object_value' if issue['issue_type'] == 'OBJECT_VALUE_UNSTRUCTURED' else 'condition_ast'
                payload[field] = issue['structured_value' if field == 'object_value' else field]
        version = claim_version_id(entity, payload)
        require(v['claim_version_id'] == claim_version_id(entity, v['semantic_payload']), 'baseline version mismatch')
        unresolved = sum(r['resolution_status'] != 'RESOLVED' for r in related)
        blocked_human = props.get('Decision') in ('HOLD', 'REJECTED') or props.get('Status') in ('HOLD', 'REJECTED') or v.get('source_system_status') in ('HOLD', 'REJECTED')
        delta = {}
        if payload != v['semantic_payload']:
            values = {'Object Value': canonical(payload['object_value']), 'Condition AST': canonical(payload['condition_ast']),
                      'Claim Entity ID': entity, 'Claim Version ID': version}
            delta = {k: {'rich_text': [{'type': 'text', 'text': {'content': val}}]} for k, val in values.items() if props.get(k) != val}
        reasons = []
        if not page or not review: reasons.append('MISSING_MAPPING_OR_BEFORE_IMAGE')
        if page and counts[page] != 1: reasons.append('MAPPING_COLLISION')
        if review.get('parent') != PARENT: reasons.append('PARENT_MISMATCH')
        if props.get('Knowledge ID') != v['legacy_canonical_id']: reasons.append('LEGACY_MAPPING_MISMATCH')
        if any(schema.get(k) != 'rich_text' for k in delta): reasons.append('SCHEMA_MISMATCH')
        if unresolved: reasons.append('UNRESOLVED_DATA_QUALITY')
        if blocked_human: reasons.append('HUMAN_OR_SOURCE_HOLD_REJECTED')
        if blocked_human: classification = 'BLOCKED_HUMAN_DECISION'
        elif reasons: classification = 'BLOCKED_DATA_QUALITY'
        elif not delta: classification = 'UNCHANGED'
        else: classification = 'ELIGIBLE_CANARY'
        before = {k: {'rich_text': [] if not props.get(k) else [{'type': 'text', 'text': {'content': props[k]}}]} for k in delta}
        # Rich text formatting is not represented by connector strings: fail closed if nonempty.
        if classification == 'ELIGIBLE_CANARY' and any(props.get(k) for k in delta):
            reasons.append('TYPED_BEFORE_IMAGE_REQUIRED'); classification = 'BLOCKED_DATA_QUALITY'
        records.append(dict(operation='UPDATE', page_id=page, entity_id=entity, version_id=version,
            baseline_version_id=v['claim_version_id'], semantic_payload=payload, classification=classification,
            reasons=reasons, unresolved_blocker_count=unresolved, live_decision=props.get('Decision'),
            decision_binding={k: deepcopy(props.get(k)) for k in sorted(HUMAN)}, field_delta=delta,
            before_image_hash=digest(before), expected_after_image_hash=digest(delta), rollback_payload=before,
            rollback_hash=digest(before), target_parent_proof=review.get('parent'),
            selection_reason='Deterministic evidence-backed typed delta; all eligibility gates passed' if classification == 'ELIGIBLE_CANARY' else None,
            human_field_exclusion_proof=not bool(set(delta) & HUMAN)))
    return records


def gate_readiness(report, canary, records):
    require(report['v161_baseline_hash_before'] == report['v161_baseline_hash_after'] == BASELINE, 'baseline hash mismatch')
    for k in ('production_write_count', 'human_field_write_count', 'create_count', 'sql_count', 'scheduler_action_count', 'schema_mutation_count'):
        require(type(report.get(k)) is int and report[k] == 0, 'missing or nonzero '+k)
    require(isinstance(canary, dict) and canary.get('authorized_to_execute') is False, 'canary not execution-disabled')
    require(isinstance(canary.get('records'), list) and len(canary['records']) <= 3, 'canary exceeds 3')
    require(len({r['page_id'] for r in canary['records']}) == len(canary['records']), 'duplicate canary page')
    for r in canary['records']:
        require(r in records and r['classification'] == 'ELIGIBLE_CANARY' and not r['reasons'], 'canary not eligible')
        require(r['operation'] == 'UPDATE' and not r['unresolved_blocker_count'], 'CREATE/blocker forbidden')
        require(r['live_decision'] not in ('HOLD', 'REJECTED'), 'human decision blocks')
        require(r['field_delta'] and set(r['field_delta']) <= SYSTEM and not set(r['field_delta']) & HUMAN, 'invalid field delta')
        require(r['target_parent_proof'] == PARENT, 'parent mismatch')
        require(r.get('selection_reason') and r.get('human_field_exclusion_proof') is True, 'missing selection/exclusion proof')
        require(r['rollback_hash'] == r['before_image_hash'] == digest(r['rollback_payload']), 'rollback hash mismatch')
        require(r['expected_after_image_hash'] == digest(r['field_delta']), 'after hash mismatch')


def compute(versions, source_issues, operations, reviews, schema, evidence=None):
    evidence = evidence or {}
    issues = inventory(versions, source_issues)
    pages = {r['claim_entity_id']: r.get('page_id') for r in operations}
    ledger = ledger_for(issues, reviews, pages, evidence)
    gate_ledger(ledger, issues, reviews, pages, evidence)
    records = plan_records(versions, operations, ledger, reviews, schema)
    eligible = [r for r in records if r['classification'] == 'ELIGIBLE_CANARY']
    canary = {'authorized_to_execute': False, 'records': eligible[:3]}
    counts = Counter(r['classification'] for r in records)
    report = dict(v161_baseline_hash_before=BASELINE, v161_baseline_hash_after=BASELINE,
        issue_count_by_type=dict(sorted(Counter(r['issue_type'] for r in ledger).items())),
        resolution_counts={k: sum(r['resolution_status'] == k for r in ledger) for k in ('RESOLVED', 'HOLD', 'NEEDS_REVIEW')},
        unresolved_issue_count=sum(r['resolution_status'] != 'RESOLVED' for r in ledger),
        eligible_record_count=len(eligible), canary_record_count=len(canary['records']),
        blocked_data_quality_count=counts['BLOCKED_DATA_QUALITY'], blocked_human_decision_count=counts['BLOCKED_HUMAN_DECISION'],
        records_with_data_quality_blockers=sum(r['unresolved_blocker_count'] > 0 for r in records),
        missing_mapping_count=sum('MISSING_MAPPING_OR_BEFORE_IMAGE' in r['reasons'] for r in records),
        mapping_collision_count=sum('MAPPING_COLLISION' in r['reasons'] for r in records),
        production_write_count=0, human_field_write_count=0, create_count=0, sql_count=0,
        scheduler_action_count=0, schema_mutation_count=0, mode='NO_WRITE')
    gate_readiness(report, canary, records)
    return {'v162_issue_ledger.json': {'issues': ledger}, 'v162_resolution_report.json': report,
        'v162_unresolved_review_queue.json': [r for r in ledger if r['resolution_status'] != 'RESOLVED'],
        'v162_canonical_plan.json': {'mode': 'NO_WRITE', 'authorized_to_execute': False, 'records': records},
        'v162_eligible_subset.json': eligible, 'v162_phase_f_canary_plan.json': canary,
        'v162_readiness_report.json': report}
