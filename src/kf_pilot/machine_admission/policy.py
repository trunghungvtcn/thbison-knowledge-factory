"""Narrow exact OEM construction facts, with provenance and legacy HOLD isolation."""
import re
import math
from html.parser import HTMLParser
from uuid import UUID, uuid5

from kf_pilot.v16.identity import V16_NAMESPACE, normalize_string
from kf_pilot.v166_evidence_completion.canonical import digest, exact, require, sha256
from kf_pilot.v166_evidence_completion.schemas import iso_time, validate_ast

POLICY_ID = 'machine_admission/v1'
EXTRACTOR = 'html-blocks/1'
# Risk and extraction are code-owned. Numeric capacities and safety claims are excluded.
PREDICATES = {
    'housing_material': {'risk': 'R1', 'use': 'DESCRIPTIVE_DRAFT',
                         'pattern': r'\b(?:die-cast aluminum (?:body|housing)|aluminium (?:body|housing))\b'},
    'drive_components': {'risk': 'R1', 'use': 'DESCRIPTIVE_DRAFT',
                        'pattern': r'\b(?:precision[- ]machined (?:gears|drive train components)|pre-lubricated ball bearings)\b'},
    'inspection_interval': {'risk': 'R3', 'use': None, 'pattern': None},
    'rated_capacity': {'risk': 'R2', 'use': 'SOURCE_SCOPED_REFERENCE', 'pattern': None},
}
POLICY_HASH = digest({'id': POLICY_ID, 'predicates': PREDICATES, 'extractor': EXTRACTOR})
SCOPE_KEYS = {'manufacturer', 'model', 'jurisdiction'}
CLAIM_KEYS = {'schema_version', 'entity_id', 'base_version_id', 'legacy_ids', 'predicate',
              'value', 'scope', 'as_of', 'corpus_revision', 'evidence', 'condition_ast', 'exception_ast'}


class Blocks(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parts, self.skipped = [], 0

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style', 'noscript'}:
            self.skipped += 1
        elif not self.skipped and tag in {'p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'br', 'td', 'tr'}:
            self.parts.append('\n')

    def handle_endtag(self, tag):
        if tag in {'script', 'style', 'noscript'}:
            self.skipped = max(0, self.skipped - 1)
        elif not self.skipped and tag in {'p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'td', 'tr'}:
            self.parts.append('\n')

    def handle_data(self, data):
        if not self.skipped:
            self.parts.append(data)


def extract(raw):
    require(len(raw) <= 20 * 1024**2, 'PARSER_SIZE_CAP')
    parser = Blocks()
    parser.feed(raw.decode('utf-8', errors='strict'))
    return '\n'.join(line for part in ''.join(parser.parts).splitlines()
                     if (line := normalize_string(part)))


def schema(claim):
    exact(claim, CLAIM_KEYS, 'MACHINE_CLAIM')
    require(type(claim['schema_version']) is int and claim['schema_version'] == 1, 'CLAIM_VERSION')
    exact(claim['scope'], SCOPE_KEYS, 'SCOPE')
    for v in claim['scope'].values():
        require(type(v) is str and 0 < len(v) <= 200, 'SCOPE_TYPE')
    exact(claim['value'], {'type', 'value', 'unit'}, 'TYPED_VALUE')
    value = claim['value']
    require(value['type'] == 'text' and type(value['value']) is str and 0 < len(value['value']) <= 400
            and value['unit'] is None, 'VALUE_TYPE')
    require(type(claim['legacy_ids']) is list and len(claim['legacy_ids']) <= 32
            and all(type(x) is str for x in claim['legacy_ids']), 'LEGACY_IDS')
    for key in ('entity_id', 'base_version_id', 'predicate'):
        require(type(claim[key]) is str and 0 < len(claim[key]) <= 200, 'CLAIM_ID_TYPE')
    require(str(UUID(claim['entity_id'])) == claim['entity_id'], 'ENTITY_UUID')
    require(type(claim['corpus_revision']) is str and bool(re.fullmatch('[a-f0-9]{64}', claim['corpus_revision'])), 'CORPUS_HASH')
    iso_time(claim['as_of'])
    for key in ('condition_ast', 'exception_ast'):
        validate_ast(claim[key])
        _finite_ast(claim[key])
    exact(claim['evidence'], {'source_id', 'raw_sha256', 'text_sha256', 'start', 'end',
                              'quote', 'context', 'extractor'}, 'EVIDENCE')
    for key in ('start', 'end'):
        require(type(claim['evidence'][key]) is int and claim['evidence'][key] >= 0, 'SPAN_OFFSET')
    for key in ('raw_sha256', 'text_sha256'):
        require(type(claim['evidence'][key]) is str and bool(re.fullmatch('[a-f0-9]{64}', claim['evidence'][key])), 'EVIDENCE_HASH')
    for key in ('source_id', 'quote', 'context', 'extractor'):
        require(type(claim['evidence'][key]) is str and 0 < len(claim['evidence'][key]) <= 100000, 'EVIDENCE_TYPE')
    return claim


def _finite_ast(node):
    if node['op'] == 'PREDICATE':
        value = node['value']
        require(type(value) in (str, bool, int, float), 'AST_VALUE_TYPE')
        require(type(value) is not float or math.isfinite(value), 'AST_NONFINITE')
        if node['cmp'] in {'GT', 'GTE', 'LT', 'LTE'}:
            require(type(value) in (int, float), 'AST_NUMERIC_TYPE')
    for child in node.get('args', []):
        _finite_ast(child)
    if 'arg' in node:
        _finite_ast(node['arg'])


def candidates(raw, source, corpus, as_of):
    text = extract(raw)
    found = {}
    for predicate, contract in PREDICATES.items():
        if not contract['pattern']:
            continue
        for m in re.finditer(contract['pattern'], text, re.I):
            start = text.rfind('\n', 0, m.start()) + 1
            end = text.find('\n', m.end())
            end = len(text) if end == -1 else end
            context = text[start:end]
            if len(context) > 4000:
                continue
            value = normalize_string(m.group(0)).lower()
            entity = str(uuid5(V16_NAMESPACE, 'machine:' + digest([source['scope'], predicate, value])))
            c = {'schema_version': 1, 'entity_id': entity, 'base_version_id': 'NEW_LOCAL',
                 'legacy_ids': [], 'predicate': predicate, 'value': {'type': 'text', 'value': value, 'unit': None},
                 'scope': source['scope'], 'as_of': as_of, 'corpus_revision': corpus,
                 'condition_ast': {'op': 'TRUE'}, 'exception_ast': {'op': 'FALSE'},
                 'evidence': {'source_id': source['source_id'], 'raw_sha256': sha256(raw),
                              'text_sha256': sha256(text.encode()), 'start': m.start(), 'end': m.end(),
                              'quote': m.group(0), 'context': context, 'extractor': EXTRACTOR}}
            found.setdefault(entity, c)
    return list(found.values())


def decide(claim, source, raw, corpus, as_of, legacy_records=(), conflicts=()):
    schema(claim)
    c = claim; e = c['evidence']; contract = PREDICATES.get(c['predicate'])
    result = {'claim_hash': digest(c), 'decision_type': 'MACHINE_POLICY', 'policy_id': POLICY_ID,
              'policy_hash': POLICY_HASH, 'risk': contract['risk'] if contract else 'UNKNOWN',
              'state': None, 'reasons': [], 'allowed_uses': [], 'authorized_to_execute': False,
              'legacy_resolution_changed': False, 'model_status': 'NOT_CALIBRATED'}
    def route(state, reason):
        result.update(state=state, reasons=[reason])
        return result
    # Exact alias and semantic scope overlap lookup precedes machine eligibility.
    ids = {c['entity_id'], *c['legacy_ids']}
    for old in legacy_records:
        held = old.get('decision', '').upper() in {'HOLD', 'HUMAN_HOLD', 'REJECTED'}
        held = held or old.get('source_system_status') == 'HOLD' or bool(old.get('blockers'))
        if not held:
            continue
        old_ids = {old['entity_id'], *old.get('aliases', [])}
        semantic = old.get('semantic_payload', {})
        old_subject = normalize_string(str(semantic.get('subject', ''))).lower()
        overlap = (c['predicate'] == semantic.get('predicate', '').lower()
                   and (old_subject == normalize_string(c['scope']['model']).lower()
                        or old_subject in {'manual hand chain hoist', 'manual chain hoist', 'pa lăng xích kéo tay'}))
        # unresolved inspection/selection stays R3 even under a new identity.
        if ids & old_ids or overlap:
            return route('HUMAN_HOLD', 'LEGACY_LINEAGE_HOLD')
    if sha256(raw) != source['raw_sha256'] or sha256(raw) != e['raw_sha256']:
        return route('QUARANTINED', 'RAW_HASH_MISMATCH')
    text = extract(raw)
    if (sha256(text.encode()) != e['text_sha256'] or text[e['start']:e['end']] != e['quote']
            or e['extractor'] != EXTRACTOR or e['source_id'] != source['source_id']):
        return route('QUARANTINED', 'SPAN_BINDING_MISMATCH')
    start = text.rfind('\n', 0, e['start']) + 1
    end = text.find('\n', e['end']); end = len(text) if end < 0 else end
    if text[start:end] != e['context']:
        return route('QUARANTINED', 'CONTEXT_BINDING_MISMATCH')
    if c['corpus_revision'] != corpus or c['as_of'] != as_of:
        return route('NEEDS_EVIDENCE', 'TEMPORAL_OR_CORPUS_MISMATCH')
    if c['scope'] != source['scope'] or source['authority'] != 'OEM' or source['access'] != 'PUBLIC':
        return route('NEEDS_EVIDENCE', 'SOURCE_SCOPE_MISMATCH')
    if not re.search(r'(?<![\w-])' + re.escape(c['scope']['model']) + r'(?![\w-])', text, re.I):
        return route('NEEDS_EVIDENCE', 'MODEL_NOT_IN_SOURCE')
    if conflicts:
        return route('REVIEW_EXCEPTION', 'CORPUS_CONFLICT')
    if not contract or contract['risk'] == 'R3':
        return route('REVIEW_EXCEPTION', 'PREDICATE_REVIEW_REQUIRED')
    if contract['risk'] == 'R2':
        return route('NEEDS_EVIDENCE', 'CALIBRATED_EVALUATOR_REQUIRED')
    if c['condition_ast'] != {'op': 'TRUE'} or c['exception_ast'] != {'op': 'FALSE'}:
        return route('NEEDS_EVIDENCE', 'UNKNOWN_OR_CONDITIONAL_CONTEXT')
    if re.search(r'\b(not|never|without|except|unless|if|must|shall|should|capacity|certif\w*|safe\w*)\b|\d', e['context'], re.I):
        return route('NEEDS_EVIDENCE', 'CONTEXT_REQUIRES_INTERPRETATION')
    if (not re.fullmatch(contract['pattern'], e['quote'], re.I)
            or c['value']['value'] != normalize_string(e['quote']).lower()):
        return route('QUARANTINED', 'PREDICATE_VALUE_UNSUPPORTED')
    result['allowed_uses'] = [contract['use']]
    return route('MACHINE_ACCEPTED', 'DIRECT_EXACT_OEM_CONSTRUCTION')


def retrieve(records, requested_use, scope, as_of, corpus):
    return [r for r in records if r['decision']['state'] == 'MACHINE_ACCEPTED'
            and requested_use in r['decision']['allowed_uses'] and r['claim']['scope'] == scope
            and r['claim']['as_of'] == as_of and r['claim']['corpus_revision'] == corpus]
