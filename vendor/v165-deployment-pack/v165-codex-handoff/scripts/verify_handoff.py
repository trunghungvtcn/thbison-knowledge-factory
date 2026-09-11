#!/usr/bin/env python3
"""Offline handoff integrity check; does not execute the Knowledge Factory repo."""
import collections
import hashlib
import json
from pathlib import Path, PurePosixPath
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
ZIP_SHA = '30054428e104f084efd2cd9dea04037c2698cf6cadee99c89e3fb911338823aa'
MANIFEST_SHA = 'd154b411445d239a3a4167cf0b52e0158dffe6f49946baa40fe476cd38148aaf'
PRIMARY = '0496c4f5-fe89-5d30-b948-34505fb64143'
SECONDARY = '59957ace-b4fb-519e-b92d-773bc74ad268'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def canonical_hash(value):
    return digest(json.dumps(value, ensure_ascii=False, sort_keys=True,
                             separators=(',', ':'), allow_nan=False).encode('utf-8'))


def load_checkpoint():
    path = ROOT / 'reference/final-003.zip'
    require(digest(path.read_bytes()) == ZIP_SHA, 'INPUT_ZIP_HASH_MISMATCH')
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        names = [i.filename for i in infos]
        require(len(names) == len(set(names)), 'DUPLICATE_ZIP_MEMBER')
        for name in names:
            p = PurePosixPath(name)
            require(not p.is_absolute() and '..' not in p.parts and
                    '\\' not in name and p.parts[0] == 'final-003', 'UNSAFE_ZIP_PATH')
        require(sum(i.file_size for i in infos) < 32 * 1024 * 1024, 'UNEXPECTED_ZIP_SIZE')
        files = {i.filename: archive.read(i) for i in infos if not i.is_dir()}
    manifest_bytes = files['final-003/artifact_hashes.json']
    require(digest(manifest_bytes) == MANIFEST_SHA, 'MANIFEST_HASH_MISMATCH')
    manifest = json.loads(manifest_bytes)
    require(len(manifest) == 14, 'MANIFEST_MEMBER_COUNT')
    require(set(files) == {'final-003/' + n for n in manifest} |
            {'final-003/artifact_hashes.json'}, 'MEMBER_SET_MISMATCH')
    for name, expected in manifest.items():
        require(digest(files['final-003/' + name]) == expected, 'MEMBER_HASH: ' + name)

    def read(name):
        raw = files['final-003/' + name]
        if name.endswith('.jsonl'):
            return [json.loads(line) for line in raw.splitlines() if line.strip()]
        return json.loads(raw)

    issues = read('v164_issue_accounting.jsonl')
    mappings = read('v164_mapping_snapshot.jsonl')
    proposals = read('v164_semantic_proposals.jsonl')
    require(len(issues) == len({r['issue_id'] for r in issues}) == 79, 'ISSUE_IDENTITIES')
    require(collections.Counter(r['issue_type'] for r in issues) ==
            {'OBJECT_VALUE_UNSTRUCTURED': 70, 'CONDITION_CONNECTIVE_AMBIGUOUS': 9}, 'ISSUE_TYPES')
    require(collections.Counter(r['resolution_status'] for r in issues) ==
            {'NEEDS_REVIEW': 68, 'HOLD': 11}, 'ISSUE_STATUS')
    require(len(mappings) == len({r['entity_id'] for r in mappings}) ==
            len({r['page_id'] for r in mappings}) == 70, 'MAPPING_IDENTITIES')
    by_entity = {r['entity_id']: r for r in mappings}
    for issue in issues:
        require(issue['entity_id'] in by_entity and issue['version_id'] ==
                by_entity[issue['entity_id']]['version_id'], 'ISSUE_MAPPING_VERSION')
    require(len(proposals) == 2 and {p['entity_id'] for p in proposals} ==
            {PRIMARY, SECONDARY}, 'PROPOSAL_SET')
    for p in proposals:
        require(canonical_hash({k: v for k, v in p.items() if k != 'proposal_hash'}) ==
                p['proposal_hash'], 'PROPOSAL_HASH')
        payload = p['target_semantic_payload']
        require(canonical_hash(payload) == p['semantic_hash'], 'SEMANTIC_HASH')
        require(canonical_hash(payload['object_value']) == p['after_value_hash'], 'VALUE_HASH')
        require(payload['condition_ast']['op'] == 'UNRESOLVED' and
                payload['exception_ast'] == {'op': 'FALSE'}, 'INHERITED_AST_STATE')
        mapping = by_entity[p['entity_id']]
        require(mapping['version_id'] == p['base_version_id'] and
                mapping['page_id'] == p['page_id'] and
                mapping['parent_id'] == p['parent_id'], 'PROPOSAL_MAPPING')
        require(any(i['issue_id'] == p['issue_id'] and i['entity_id'] == p['entity_id']
                    for i in issues), 'PROPOSAL_ISSUE')
    for name in ['v164_review_results.jsonl', 'v164_accepted_derivations.jsonl',
                 'v164_adapter_inputs.jsonl']:
        require(read(name) == [], 'EXPECTED_EMPTY: ' + name)
    canary = read('v164_phase_f_canary_plan.json')
    require(canary['authorized_to_execute'] is False and canary['records'] == [], 'CANARY_STATE')
    return issues, mappings, proposals, read('v164_contract_gap_report.json')


def derive_targets(checkpoint):
    issues, mappings, proposals, gap = checkpoint
    targets = []
    for role, entity in [('PRIMARY', PRIMARY), ('CONTEXT_AND_REGRESSION', SECONDARY)]:
        p = next(p for p in proposals if p['entity_id'] == entity)
        targets.append({
            'role': role,
            'mapping': next(m for m in mappings if m['entity_id'] == entity),
            'issues': sorted([i for i in issues if i['entity_id'] == entity],
                             key=lambda i: i['issue_id']),
            'v164_proposal': p,
            'page_mapping_reported_requires_raw_verification': gap['pdf_page_mapping'],
            'v165_target_version_id': None,
            'semantic_adjudication': 'NOT_SUPPLIED',
            'production_authorized': False,
        })
    return {'classification': 'CHECKPOINT_REFERENCE_NOT_APPROVAL',
            'input_zip_sha256': ZIP_SHA, 'input_manifest_sha256': MANIFEST_SHA,
            'selection_basis': 'Fewer legacy condition tags; no legal validity inference.',
            'targets': targets}


def verify():
    checkpoint = load_checkpoint()
    actual = json.loads((ROOT / 'reference/targets.json').read_text(encoding='utf-8'))
    require(actual == derive_targets(checkpoint), 'TARGET_REFERENCE_MISMATCH')
    activation = json.loads((ROOT / 'contracts/contract_activation.template.json').read_text(encoding='utf-8'))
    require(activation['decision'] == 'NOT_APPROVED' and
            activation['classification'] == 'DRAFT_TEMPLATE_NOT_APPROVED' and
            activation['production_authorized'] is False and
            activation['contract_spec_hash'] is None and activation['issuer_id'] is None,
            'TEMPLATE_MUST_NOT_AUTHORIZE')
    for filename in ['README.md', 'PROMPT_CODEX_V165.md', 'IMPLEMENTATION_PLAN.md',
                     'contracts/COMPLETE_RECORD_V1.md', 'docs/ACCEPTANCE_MATRIX.md',
                     'docs/EXPECTED_REPORT.md', 'docs/VERIFICATION_SCOPE.md']:
        require((ROOT / filename).is_file(), 'MISSING_DOCUMENT: ' + filename)
    return {'status': 'V165_HANDOFF_PACK_VERIFIED', 'input_zip_sha256': ZIP_SHA,
            'manifest_members_verified': 14, 'checkpoint_regular_files': 15,
            'mappings': 70, 'issues': 79, 'proposals_rehashed': 2,
            'scope': 'LOCAL_PACKAGE_INTEGRITY_ONLY', 'repository_tests_run': False,
            'raw_sources_reextracted': False, 'production_authorized': False}


if __name__ == '__main__':
    try:
        print(json.dumps(verify(), ensure_ascii=False, indent=2))
    except (ValueError, KeyError, OSError, zipfile.BadZipFile) as error:
        print('V165_HANDOFF_PACK_FAIL: ' + str(error), file=sys.stderr)
        sys.exit(1)
