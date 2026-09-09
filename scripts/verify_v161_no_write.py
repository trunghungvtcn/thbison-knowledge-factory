"""Verify local/remote plans and replay the actual baseline without network."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

def digest(value):
    return hashlib.sha256(json.dumps(value,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False).encode()).hexdigest()

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--root',type=Path,required=True)
    parser.add_argument('--inputs',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    sys.path.insert(0,str(args.root/'src'))
    from kf_pilot.v16.migration import LegacyCanonicalRow,migrate_row
    from kf_pilot.v16.notion_payload import build_update_only_plan
    raw=json.loads((args.inputs/'v15_canonical_rows.json').read_text(encoding='utf-8'))
    def run(data):
        return sorted([migrate_row(LegacyCanonicalRow.model_validate(r),'REPLAY') for r in data],key=lambda r:r.entity['claim_entity_id'])
    a,b=run(raw),run(list(reversed(raw)))
    assert [r.entity for r in a]==[r.entity for r in b]
    assert [r.version for r in a]==[r.version for r in b]
    changed=[dict(r) for r in raw]
    changed[0]['parsed_condition_ast']={'op':'FALSE'}
    c=run(changed)
    assert [r.entity['claim_entity_id'] for r in a]==[r.entity['claim_entity_id'] for r in c]
    assert sum(x.version['claim_version_id']!=y.version['claim_version_id'] for x,y in zip(a,c))==1
    assert [r.publication_mapping for r in a]==[r.publication_mapping for r in c]
    report=json.loads((args.output/'prepublication_validation_report.json').read_text(encoding='utf-8'))
    plan=json.loads((args.output/'notion_typed_update_plan.json').read_text(encoding='utf-8'))
    expected={'update_count':70,'create_count':0,'missing_mapping_count':0,'mapping_collision_count':0,'human_field_write_count':0,'remote_writes':0,'schema_type_mismatch_count':0}
    for key,value in expected.items():
        assert report[key]==value,(key,report[key])
    assert len(plan['operations'])==70
    assert len({o['page_id'] for o in plan['operations']})==70
    forbidden={'Decision','Reviewer Note','Reviewer','Review Notes','Editorial Notes','Manual Tags','Approval Timestamp','Reviewed Entity ID','Reviewed Version ID'}
    assert all(o['operation']=='UPDATE' and not (set(o['typed_properties']) & forbidden) for o in plan['operations'])
    references=json.loads((args.inputs/'live_knowledge_snapshot.json').read_text(encoding='utf-8'))
    bypage={r['page_id']:r for r in references}
    bindings=[json.loads(line) for line in (args.output/'decision_bindings.jsonl').read_text(encoding='utf-8').splitlines()]
    byentity={r['claim_entity_id']:r for r in bindings}
    for operation in plan['operations']:
        live=bypage[operation['page_id']]
        binding=byentity[operation['claim_entity_id']]
        assert binding['notes']==live['reviewer_note']
        assert binding['decision']==live['decision']
        assert operation['effective_decision']!='APPROVED'
    validation={'gates':expected,'reverse_order_replay':'PASS','single_semantic_change':'PASS',
        'human_notes_preserved':True,'plan_sha256':digest(plan),'remote_write_capability':False}
    expected_file=args.inputs/'expected_local_plan.json'
    if expected_file.exists():
        assert digest(json.loads(expected_file.read_text(encoding='utf-8')))==digest(plan),'local/remote plan mismatch'
        validation['local_remote_plan_equal']=True
    (args.output/'acceptance_checks.json').write_text(json.dumps(validation,indent=2),encoding='utf-8')
    print(json.dumps(validation,indent=2))

if __name__=='__main__':main()
