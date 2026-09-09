"""Rebuild evidence-bound R3 research proposals; never project them or infer legal truth."""
import argparse
import copy
from pathlib import Path

from .pipeline import ROOT, LEGACY, invariant
from .storage import atomic
from kf_pilot.v166_evidence_completion.canonical import confined, digest, load, require, rows, sha256
from kf_pilot.v166_evidence_completion.schemas import validate_ast

SPECS = [
    ('qtkd13-section10-pdf67', 'v166/corpus/completion-001', 'tt54-2016-gazette-431-432', 67, '68', '10. THỜI HẠN KIỂM ĐỊNH', None),
    ('qtkd13-scope-pdf62', 'v166/corpus/completion-001', 'tt54-2016-gazette-431-432', 62, '63', '1. PHẠM VI', '2. TÀI LIỆU VIỆN DẪN'),
    ('tt19-2025-pdf8', 'v166/corpus/frozen-001', 'tt19-2025-bnv-official-pdf', 8, '6', None, None),
]


def source_span(spec):
    import pymupdf
    span_id, directory, source_id, ordinal, printed, start_text, end_text = spec
    root = ROOT / directory; manifest = load(root/'frozen_corpus_manifest.json')
    declared = manifest['corpus_revision']; material = dict(manifest); material.pop('corpus_revision')
    require(digest(material) == declared, 'LEGACY_CORPUS_HASH')
    source = next(s for s in manifest['sources'] if s['source_id'] == source_id)
    file = confined(root, source['local_path'])
    require(sha256(file.read_bytes()) == source['sha256'], 'LEGACY_RAW_HASH')
    with pymupdf.open(file) as doc:
        text = doc[ordinal-1].get_text('text', sort=True)
    start = text.index(start_text) if start_text else 0
    end = text.index(end_text, start) if end_text else len(text)
    require(end > start, 'LEGACY_SPAN_EMPTY')
    # Retain the full table page context for tt19; extraction is not a legal applicability judgement.
    return {'span_id': span_id, 'source_id': source_id, 'source_url': source['final_url'],
            'source_manifest': directory+'/frozen_corpus_manifest.json', 'source_corpus_revision': declared,
            'source_as_of': manifest['as_of'], 'raw_path': directory+'/'+source['local_path'],
            'raw_sha256': source['sha256'], 'text_sha256': sha256(text.encode()),
            'extractor': 'pymupdf/'+pymupdf.VersionBind, 'options': {'sort': True, 'normalization': 'NONE'},
            'page_index': ordinal-1, 'page_ordinal': ordinal, 'printed_label': printed,
            'start': start, 'end': end, 'quote': text[start:end], 'context': text,
            'checked_from_raw': True, 'semantic_legal_applicability': 'NOT_ADJUDICATED'}


def build():
    before = invariant()
    spans = [source_span(s) for s in SPECS]
    corpus = {'schema_version': 1, 'parent_revision': spans[-1]['source_corpus_revision'],
              'source_corpus_revisions': sorted({s['source_corpus_revision'] for s in spans}),
              'legal_as_of': '2026-09-05T00:00:00+07:00', 'as_of': '2026-09-08T00:00:00+07:00',
              'temporal_delta': 'Bind raw evidence gathered in 05/09 and 07/09 revisions without moving legacy legal_as_of or adjudicating current applicability.',
              'span_hashes': {s['span_id']: digest(s) for s in spans}}
    corpus['corpus_revision'] = digest(corpus)
    ledger = load(ROOT/LEGACY['ledger'])['issues']
    proposals = []
    for old in rows(ROOT/'v166/artifacts/proposal-004/interpretation_candidates.jsonl'):
        p = copy.deepcopy(old); p.pop('proposal_hash', None)
        p['corpus_revision'] = corpus['corpus_revision']
        p['as_of'] = corpus['legal_as_of']
        p['state'] = 'WAITING_EVIDENCE'
        p['evidence_span_ids'] = [s['span_id'] for s in spans]
        p['original_issue_ids'] = sorted(i['issue_id'] for i in ledger if i['entity_id'] == p['entity_id'])
        p['after_semantic_payload']['exception_ast'] = {'op': 'UNRESOLVED', 'reason': 'SECTIONS_10_2_10_4_ENCODING_AND_PRECEDENCE_NOT_ADJUDICATED'}
        p['gap_assessment'] = {k: 'INTERPRETATION_REVIEW_REQUIRED' for k in ('conditions','exceptions','overlap','legal_time')}
        p['actual_field_diff'] = sorted(k for k, v in p['after_semantic_payload'].items() if p['current_record']['semantic_payload'].get(k) != v)
        p['target_version_id'] = None
        p['proposal_hash'] = digest(p)
        proposals.append(p)
    require(len(proposals) == 2, 'LEGACY_PILOT_COUNT')
    require(before == invariant(), 'LEGACY_MUTATION')
    return {'corpus': corpus, 'spans': spans, 'proposals': proposals, 'authorized_to_execute': False}


def verify(package):
    # Re-open raw documents, all ledger records and original proposals; hash replacement alone cannot pass.
    expected = build()
    require(package == expected, 'LEGACY_BINDING_RECOMPUTE_FAILED')
    for p in package['proposals']:
        require(p['base_version_id'] == p['current_record']['version_id'], 'LEGACY_BASE')
        require(p['authorized_to_execute'] is False and p['target_version_id'] is None, 'LEGACY_NOT_AUTHORIZED')
        for key in ('condition_ast','exception_ast'):
            validate_ast(p['after_semantic_payload'][key])
            require(p['after_semantic_payload'][key]['op'] == 'UNRESOLVED', 'LEGACY_AMBIGUITY_LOST')
        require(p['original_issue_ids'], 'LEGACY_ISSUE_ACCOUNTING')
    return {'status': 'CURRENT_PASS', 'raw_binding_only': True, 'spans': len(package['spans']),
            'proposals': len(package['proposals']), 'proposal_status': 'NOT_READY_FOR_ADJUDICATION',
            'semantic_legal_applicability': 'NOT_ADJUDICATED', 'authorized_to_execute': False}


def main():
    p = argparse.ArgumentParser(); p.add_argument('--output', required=True); args = p.parse_args()
    root = Path(args.output); package = build(); atomic(root/'bindings-private.json', package)
    result = verify(load(root/'bindings-private.json'))
    atomic(root/'attestation.json', result)
    print(result)


if __name__ == '__main__':
    main()
