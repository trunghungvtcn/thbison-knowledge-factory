"""Strict whole-record proposals and atomic, in-memory shadow projection."""
from copy import deepcopy
from datetime import datetime

from kf_pilot.v16.identity import claim_version_id
from kf_pilot.v16.condition_ast import canonicalize_ast, contains_unresolved
from kf_pilot.v162_remediation.core import resolve
from kf_pilot.v164_semantics.canonical import digest, require, exact_keys
from kf_pilot.v164_semantics.interpretation import decimal_text

CONTRACT = 'complete_record_derivation/v1'
IDENTITY = 'kf_pilot.v16.identity.claim_version_id/v1'
FIELDS = {'product_family', 'subject', 'predicate', 'object_value', 'applicability',
          'jurisdiction', 'legal_status', 'condition_ast', 'exception_ast'}
CHANGES = {'object_value', 'condition_ast', 'exception_ast', 'applicability', 'jurisdiction', 'legal_status'}
CHECKS = {'source', 'quantity', 'condition_logic', 'exceptions', 'applicability',
          'jurisdiction', 'legal_status', 'overlap', 'no_omitted_requirements'}
ASSESSMENTS = {'quantity', 'conditions', 'exceptions', 'applicability', 'jurisdiction',
               'legal_status', 'overlap', 'reviewed_scope'}
PROPOSAL_FIELDS = {'contract_id','contract_version','contract_spec_hash','identity_contract_id',
    'data_class','mode','entity_id','base_version_id','target_version_id','page_id','parent_id',
    'original_issue_ids','before_record_hash','after_semantic_hash','before_semantic_payload',
    'after_semantic_payload','allowed_changed_fields','actual_field_diff','source_bundle',
    'field_support_map','completeness_assessments','source_coverage_hash',
    'upstream_v164_proposal_hashes','dependency_records','new_blockers','status','proposer_id','proposal_hash'}


def coverage_hash(proposal):
    return digest({k: proposal[k] for k in ('source_bundle','field_support_map',
                  'completeness_assessments','dependency_records')})


def ast_paths(node, path):
    result = [path]
    for i, child in enumerate(node.get('args', [])):
        result.extend(ast_paths(child, path + '/args/' + str(i)))
    if 'arg' in node:
        result.extend(ast_paths(node['arg'], path + '/arg'))
    return result


def completeness_errors(payload, assessments, support):
    errors = []
    required = {'quantity':'SUPPORTED','conditions':'SUPPORTED','applicability':'SUPPORTED',
                'jurisdiction':'SUPPORTED','legal_status':'SUPPORTED'}
    for key, status in required.items():
        if assessments.get(key) != status:
            errors.append(key.upper() + '_EVIDENCE_INCOMPLETE')
    if contains_unresolved(payload['condition_ast']):
        errors.append('CONDITION_EVIDENCE_INCOMPLETE')
    if (contains_unresolved(payload['exception_ast']) or assessments.get('exceptions') not in
            {'EVIDENCE_BACKED','NO_APPLICABLE_EXCEPTION_IN_REVIEWED_SCOPE'}):
        errors.append('EXCEPTION_COVERAGE_UNKNOWN')
    if assessments.get('overlap') not in {'NO_CONFLICT_IN_REVIEWED_SCOPE','EVIDENCE_BACKED_PRECEDENCE'}:
        errors.append('RULE_OVERLAP_UNRESOLVED')
    if not assessments.get('reviewed_scope'):
        errors.append('SOURCE_COVERAGE_UNKNOWN')
    paths = ['object_value/amount','object_value/unit','object_value/operator',
             'applicability','jurisdiction','legal_status','overlap']
    paths += ast_paths(payload['condition_ast'], 'condition_ast')
    paths += ast_paths(payload['exception_ast'], 'exception_ast')
    for path in paths:
        if not support.get(path):
            errors.append('FIELD_SUPPORT_MISSING:' + path)
    return sorted(set(errors))


def build_proposal(record, after, issues, spans, support, assessments, spec_hash,
                   *, dependencies=(), upstream=(), blockers=(), data_class='REPOSITORY'):
    before = deepcopy(record['semantic_payload'])
    after = deepcopy(after)
    exact_keys(before, FIELDS)
    exact_keys(after, FIELDS)
    exact_keys(assessments, ASSESSMENTS)
    for key in ('condition_ast','exception_ast'):
        after[key] = canonicalize_ast(after[key])
    changed = sorted(key for key in FIELDS if before[key] != after[key])
    require(set(changed) <= CHANGES, 'UNKNOWN_FIELD_CHANGE')
    issue_ids = sorted(i['issue_id'] for i in issues if i['entity_id'] == record['entity_id'])
    require(len(issue_ids) == len(set(issue_ids)) and bool(issue_ids), 'ISSUE_SET_CHANGED')
    complete = not completeness_errors(after, assessments, support) and not blockers
    proposal = dict(contract_id=CONTRACT, contract_version=1, contract_spec_hash=spec_hash,
        identity_contract_id=IDENTITY,data_class=data_class,mode='LOCAL_SHADOW',
        entity_id=record['entity_id'],base_version_id=record['version_id'],
        target_version_id=claim_version_id(record['entity_id'],after) if complete else None,
        page_id=record['page_id'],parent_id=record['parent_id'],original_issue_ids=issue_ids,
        before_record_hash=digest(record),after_semantic_hash=digest(after),
        before_semantic_payload=before,after_semantic_payload=after,
        allowed_changed_fields=sorted(CHANGES),actual_field_diff=changed,
        source_bundle=sorted(deepcopy(spans),key=digest),
        field_support_map={k:sorted(set(v)) for k,v in sorted(support.items())},
        completeness_assessments=deepcopy(assessments),
        upstream_v164_proposal_hashes=sorted(upstream),
        dependency_records=sorted(deepcopy(list(dependencies)),key=digest),
        new_blockers=sorted(deepcopy(list(blockers)),key=digest),
        status='COMPLETE_PENDING_REVIEW' if complete else 'DRAFT',proposer_id='KF_V165_BUILDER')
    proposal['source_coverage_hash'] = coverage_hash(proposal)
    proposal['proposal_hash'] = digest(proposal)
    return proposal


def validate_bundle(p, record, issues, store, spec_hash, data_class):
    exact_keys(p, PROPOSAL_FIELDS)
    require(p['contract_id'] == CONTRACT and type(p['contract_version']) is int and p['contract_version'] == 1 and
            p['contract_spec_hash'] == spec_hash and p['identity_contract_id'] == IDENTITY,
            'CONTRACT_PIN_MISMATCH')
    require(p['data_class'] == data_class and data_class in {'TEST_ONLY','REPOSITORY'}, 'TEST_DATA_IN_REPOSITORY')
    require(p['mode'] == 'LOCAL_SHADOW', 'INVALID_MODE')
    require(p['proposal_hash'] == digest({k:v for k,v in p.items() if k!='proposal_hash'}), 'PROPOSAL_HASH_MISMATCH')
    require(p['source_coverage_hash'] == coverage_hash(p), 'SOURCE_COVERAGE_HASH_MISMATCH')
    require(p['entity_id'] == record['entity_id'] and p['base_version_id'] == record['version_id'], 'BASE_VERSION_CHANGED')
    require(p['page_id'] == record['page_id'] and p['parent_id'] == record['parent_id'], 'MAPPING_MISMATCH')
    require(p['before_record_hash'] == digest(record), 'BEFORE_IMAGE_CHANGED')
    require(p['before_semantic_payload'] == record['semantic_payload'], 'BEFORE_SEMANTICS_CHANGED')
    expected = sorted(i['issue_id'] for i in issues if i['entity_id']==record['entity_id'])
    require(p['original_issue_ids'] == expected and len(expected)==len(set(expected)), 'ISSUE_SET_CHANGED')
    for issue in issues:
        if issue['entity_id']!=record['entity_id']:continue
        require(issue['version_id']==record['version_id'],'ISSUE_VERSION_CHANGED')
        require(issue['issue_type'] in {'OBJECT_VALUE_UNSTRUCTURED','CONDITION_CONNECTIVE_AMBIGUOUS'},'UNSUPPORTED_ISSUE_BLOCKER')
        field='object_value' if issue['issue_type']=='OBJECT_VALUE_UNSTRUCTURED' else 'condition_ast'
        value=record['semantic_payload'][field]
        if field=='object_value' and value.get('type')=='legacy_text':value=value['value']
        require(issue['before_value_hash']==digest(value),'ISSUE_BEFORE_HASH_CHANGED')
    require(record['version_id'] == claim_version_id(record['entity_id'], record['semantic_payload']), 'BASE_VERSION_CHANGED')
    exact_keys(p['after_semantic_payload'], FIELDS)
    exact_keys(p['completeness_assessments'], ASSESSMENTS)
    after = p['after_semantic_payload']
    diff = sorted(k for k in FIELDS if after[k] != record['semantic_payload'][k])
    require(p['allowed_changed_fields']==sorted(CHANGES) and set(diff)<=CHANGES and diff==p['actual_field_diff'], 'UNKNOWN_FIELD_CHANGE')
    require(p['after_semantic_hash']==digest(after), 'SEMANTIC_HASH_MISMATCH')
    spans = {digest(s):s for s in p['source_bundle']}
    require(len(spans)==len(p['source_bundle']) and bool(spans), 'SOURCE_COVERAGE_UNKNOWN')
    for span in spans.values():
        store.verify(span)
    old_value=record['semantic_payload']['object_value']
    if old_value.get('type')=='legacy_text':
        require(any(' '.join(old_value['value'].split()) in ' '.join(s['quote'].split()) for s in spans.values()),
                'FULL_LEGACY_CONTEXT_MISSING')
    for refs in p['field_support_map'].values():
        require(isinstance(refs,list) and set(refs)<=spans.keys(), 'SUPPORT_REFERENCE_MISMATCH')
    errors = completeness_errors(after,p['completeness_assessments'],p['field_support_map'])
    require(not errors and not p['new_blockers'], 'INCOMPLETE_RECORD', ';'.join(errors))
    value=after['object_value']
    exact_keys(value, {'type','amount','unit','operator'})
    require(value['type']=='quantity' and value['unit']=='year' and value['operator']=='EQ', 'QUANTITY_CONTRACT_MISMATCH')
    amount=decimal_text(value['amount'])
    for field in ('amount','unit'):
        refs=p['field_support_map']['object_value/'+field]
        require(len(refs)==1, 'AMBIGUOUS_QUANTITY_PROOF')
        span=spans[refs[0]]
        store.complete_token(span,numeric=field=='amount')
        require(decimal_text(span['quote'])==amount if field=='amount' else span['quote'] in {'năm','year','years'}, 'QUANTITY_NOT_PROVEN')
    require(p['status']=='COMPLETE_PENDING_REVIEW' and
            p['target_version_id']==claim_version_id(record['entity_id'],after) and
            p['target_version_id']!=record['version_id'], 'INVALID_TARGET_VERSION')
    return True


def _time(text):
    value=datetime.fromisoformat(text.replace('Z','+00:00'))
    require(value.tzinfo is not None, 'TIMEZONE_REQUIRED')
    return value


def validate_receipts(p, roots, pins, as_of):
    require(set(roots)==set(pins)=={'registry','activation','adjudication'}, 'TRUST_ROOTS_INCOMPLETE')
    for key in roots:
        require(digest(roots[key])==pins[key], 'TRUST_ROOT_PIN_MISMATCH', key)
    registry,activation,review=(roots[k] for k in ('registry','activation','adjudication'))
    require(registry.get('data_class')==p['data_class'], 'TEST_DATA_IN_REPOSITORY')
    require(activation is not None, 'CONTRACT_NOT_ACTIVATED')
    require(review is not None, 'REVIEW_REQUIRED')
    exact_keys(activation, {'data_class','contract_spec_hash','activation_id','issuer_id','issuer_role',
        'decision','allowed_predicates','target_entity_ids','mode','valid_from','valid_until','approval_evidence_ref','registry_hash'})
    exact_keys(review, {'data_class','proposal_hash','contract_spec_hash','entity_id','base_version_id','target_version_id',
        'original_issue_ids','source_coverage_hash','reviewer_id','registry_hash','decided_at','decision','rationale','checks'})
    now=_time(as_of)
    require(activation['data_class']==review['data_class']==p['data_class'], 'TEST_DATA_IN_REPOSITORY')
    require(activation['registry_hash']==review['registry_hash']==digest(registry), 'REGISTRY_HASH_MISMATCH')
    require(activation['contract_spec_hash']==p['contract_spec_hash'] and activation['decision']=='APPROVE_LOCAL_SHADOW'
        and activation['mode']=='LOCAL_SHADOW' and activation['approval_evidence_ref'] and activation['activation_id'], 'CONTRACT_NOT_ACTIVATED')
    require(p['entity_id'] in activation['target_entity_ids'] and
        p['after_semantic_payload']['predicate'] in activation['allowed_predicates'], 'ACTIVATION_SCOPE_MISMATCH')
    require(_time(activation['valid_from'])<=now<=_time(activation['valid_until']), 'ACTIVATION_EXPIRED')
    require(activation['issuer_role']=='CONTRACT_APPROVER', 'ISSUER_ROLE_MISMATCH')
    for person,role in ((activation['issuer_id'],'CONTRACT_APPROVER'),(review['reviewer_id'],'SEMANTIC_REVIEWER')):
        require(person!=p['proposer_id'],'SELF_ADJUDICATION')
        actor=registry['entries'].get(person)
        require(actor is not None and actor.get('active') is True, 'UNTRUSTED_REVIEWER')
        require(actor.get('data_class')==p['data_class'], 'TEST_DATA_IN_REPOSITORY')
        require(role in actor['roles'] and p['after_semantic_payload']['predicate'] in actor['predicates']
            and p['entity_id'] in actor['entity_ids'], 'REVIEWER_SCOPE_MISMATCH')
        require(_time(actor['valid_from'])<=now<=_time(actor['valid_until']), 'REVIEWER_EXPIRED')
    require(review['reviewer_id']!=p['proposer_id'], 'SELF_ADJUDICATION')
    for field in ('proposal_hash','contract_spec_hash','entity_id','base_version_id','target_version_id','original_issue_ids','source_coverage_hash'):
        require(review[field]==p[field], 'REVIEW_BINDING_STALE', field)
    decided=_time(review['decided_at'])
    actor=registry['entries'][review['reviewer_id']]
    require(_time(actor['valid_from'])<=decided<=now, 'REVIEW_TIME_INVALID')
    require(review['decision']=='ACCEPT' and bool(review['rationale'].strip()), 'REVIEW_REQUIRED')
    require(set(review['checks'])==CHECKS and all(v is True for v in review['checks'].values()), 'INCOMPLETE_REVIEW')


def project(p, records, issues, store, spec_hash, data_class, roots, pins, as_of,
            expected_parent, schema, *, fail_after_stage=False):
    """Return a new projection only after all checks. Never change caller objects."""
    require(len({r['entity_id'] for r in records})==len(records) and
        len({r['page_id'] for r in records})==len(records) and all(r['page_id'] and r['parent_id'] for r in records), 'MAPPING_COLLISION_OR_MISSING')
    require(len({i['issue_id'] for i in issues})==len(issues), 'ISSUE_SET_CHANGED')
    record=next((r for r in records if r['entity_id']==p['entity_id']),None)
    require(record is not None, 'ENTITY_NOT_FOUND')
    require(record['parent_id']==expected_parent, 'PARENT_MISMATCH')
    require(all(schema.get(k)=='rich_text' for k in ('Object Value','Condition AST','Claim Entity ID','Claim Version ID')), 'SCHEMA_MISMATCH')
    by_entity={r['entity_id']:r for r in records}
    for dependency in p['dependency_records']:
        current=by_entity.get(dependency['entity_id'])
        require(current is not None and dependency['version_id']==current['version_id'] and
            dependency['record_hash']==digest(current),'DEPENDENCY_CHANGED')
    require(record['decision'] not in {'HOLD','REJECTED'} and record['system_status'] not in {'HOLD','REJECTED'}, 'HUMAN_HOLD')
    validate_bundle(p,record,issues,store,spec_hash,data_class)
    validate_receipts(p,roots,pins,as_of)
    shadow_records,shadow_issues=deepcopy(records),deepcopy(issues)
    target=next(r for r in shadow_records if r['entity_id']==p['entity_id'])
    target.update(semantic_payload=deepcopy(p['after_semantic_payload']),version_id=p['target_version_id'])
    require(not fail_after_stage, 'ATOMIC_PROJECTION_FAILED')
    events=[]
    for issue in shadow_issues:
        if issue['issue_id'] in p['original_issue_ids']:
            require(issue['resolution_status'] not in {'RESOLVED','HOLD'}, 'ISSUE_NOT_RESOLVABLE')
            event=dict(original_issue_id=issue['issue_id'],before_value_hash=issue['before_value_hash'],
                base_version_id=p['base_version_id'],target_version_id=p['target_version_id'],
                proposal_hash=p['proposal_hash'],receipt_hash=digest(roots['adjudication']))
            issue.update(resolution_status='RESOLVED',resolution_event=event)
            events.append(event)
    require(len(events)==len(p['original_issue_ids']), 'ATOMIC_PROJECTION_FAILED')
    return {'records':shadow_records,'issues':shadow_issues,'events':sorted(events,key=digest),
            'publication_review':'STALE_REQUIRES_TARGET_VERSION_REVIEW','authorized_to_execute':False}


def dispatch(route, **kwargs):
    if route=='legacy_literal/v1':
        return resolve(kwargs['issue'],kwargs['evidence'])
    if route==CONTRACT:
        return project(**kwargs)
    require(False,'UNKNOWN_CONTRACT')
