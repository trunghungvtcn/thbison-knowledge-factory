import importlib.util
import json
import sys
from pathlib import Path
import pytest
from kf_pilot.v16.migration import LegacyCanonicalRow, migrate_row
from kf_pilot.v16.notion_payload import build_update_only_plan
from kf_pilot.v16.notion_adapter import notion_schema_diff

ROOT = Path(__file__).resolve().parents[1]

def test_real_notion_types():
    assert not notion_schema_diff({'Knowledge ID':'rich_text','Applicability Scope':'rich_text'})['type_mismatches']

def test_rejected_without_bindings_stays_rejected():
    result = migrate_row(LegacyCanonicalRow(legacy_canonical_id='a', canonical_text='text',
        predicate='test', object_value='legacy', notion_page_id='p',system_status='REJECTED'), 'test')
    plan = build_update_only_plan([result.version],[result.publication_mapping],run_id='test')
    assert plan['operations'][0]['logical_properties']['system_status'] == 'REJECTED'
    with pytest.raises(ValueError):
        build_update_only_plan([result.version,result.version],[result.publication_mapping],run_id='test')

@pytest.mark.parametrize('live_status,structured', [('HOLD',True),('REJECTED',True),('REVIEW_REQUIRED',False)])
def test_cli_live_blocking_and_no_network(tmp_path, monkeypatch, live_status, structured):
    import socket
    monkeypatch.setattr(socket.socket, 'connect', lambda *args: pytest.fail('Network forbidden'))
    obj = {'type':'enum','value':'ANNUAL'} if structured else 'legacy annual text'
    row = dict(legacy_canonical_id='a',canonical_text='text',predicate='test',object_value=obj,notion_page_id='p')
    result = migrate_row(LegacyCanonicalRow(**row),'test')
    snapshot = [dict(page_id='p',legacy_id='a',decision='APPROVED',reviewer_note='keep exactly',
        status=live_status,reviewed_entity_id=result.entity['claim_entity_id'],reviewed_version_id=result.version['claim_version_id'])]
    for name,data in [('input', [row]), ('snapshot',snapshot)]:
        (tmp_path / (name+'.json')).write_text(json.dumps(data),encoding='utf-8')
    spec=importlib.util.spec_from_file_location('migrate_cli', ROOT/'notebooks/30_migrate_v16.py')
    module=importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    monkeypatch.setattr(sys,'argv',['migration','--input',str(tmp_path/'input.json'),'--live-review-snapshot',
        str(tmp_path/'snapshot.json'),'--output-dir',str(tmp_path/'output'),'--expected-count','1'])
    module.main()
    binding=json.loads((tmp_path/'output/decision_bindings.jsonl').read_text(encoding='utf-8'))
    assert binding['effective_decision'] != 'APPROVED'
    assert binding['notes'] == 'keep exactly'
