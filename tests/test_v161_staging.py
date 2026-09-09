from copy import deepcopy
import json
from pathlib import Path
from uuid import UUID, uuid5
import pytest
from kf_pilot.v161_staging.harness import Blocked, GuardedAdapter, PRODUCTION_IDS, run_cycle, validate_plan
from kf_pilot.v161_staging.transports import MemoryTransport, NotionStagingTransport

ROOT = Path(__file__).resolve().parents[1]
NS = UUID('c6a5d339-eab8-41b0-8060-280cfac60809')
TARGET = str(uuid5(NS, 'OFFLINE-MEMORY-TARGET'))
PAGES = [str(uuid5(NS, f'V161-STAGING-SYNTH-{i:03d}')) for i in range(1,4)]

@pytest.fixture
def plan():
    return json.loads((ROOT/'staging/synthetic_staging_plan.json').read_text(encoding='utf-8'))

def adapter(plan, transport=None):
    return GuardedAdapter(transport or MemoryTransport(TARGET, PAGES, plan), plan, 'STAGING', TARGET, PAGES)

@pytest.mark.parametrize('environment', ['', 'PRODUCTION', 'staging'])
def test_wrong_environment(plan, environment):
    with pytest.raises(Blocked):validate_plan(plan, environment, TARGET, PAGES)

def test_missing_target(plan):
    with pytest.raises(Blocked):validate_plan(plan,'STAGING',None,PAGES)

@pytest.mark.parametrize('target', sorted(PRODUCTION_IDS))
def test_production_target_blocked(plan,target):
    with pytest.raises(Blocked):validate_plan(plan,'STAGING',target,PAGES)

def test_production_page_and_duplicates_blocked(plan):
    with pytest.raises(Blocked):validate_plan(plan,'STAGING',TARGET,[PAGES[0],PAGES[0],PAGES[2]])
    with pytest.raises(Blocked):validate_plan(plan,'STAGING',TARGET,PAGES,denied=[PAGES[0]])

def test_more_than_three(plan):
    plan['records'].append(deepcopy(plan['records'][0]))
    with pytest.raises(Blocked):validate_plan(plan,'STAGING',TARGET,PAGES+[str(uuid5(NS,'4'))])

@pytest.mark.parametrize('key,value', [('synthetic',False),('operation','CREATE'),('environment','PRODUCTION'),('synthetic_id','REAL-ID')])
def test_record_guards(plan,key,value):
    plan['records'][0][key]=value
    with pytest.raises(Blocked):validate_plan(plan,'STAGING',TARGET,PAGES)

@pytest.mark.parametrize('field', ['Decision','Reviewer Note','Reviewed Entity ID','Reviewed Version ID','Unknown'])
def test_human_unknown_properties(plan,field):
    plan['records'][0]['properties'][field]={'rich_text':[]}
    with pytest.raises(Blocked):validate_plan(plan,'STAGING',TARGET,PAGES)

@pytest.mark.parametrize('route', ['schema_mutation','sql','scheduler'])
def test_forbidden_routes(plan,route):
    plan[route]=True
    with pytest.raises(Blocked):validate_plan(plan,'STAGING',TARGET,PAGES)

def test_full_cycle_idempotency_rollback_artifacts(plan,tmp_path,monkeypatch):
    import socket
    monkeypatch.setattr(socket.socket,'connect',lambda *a:pytest.fail('no network in local harness'))
    a=adapter(plan)
    original=deepcopy(a.transport.pages)
    output=tmp_path/'cycle'
    patch=a.transport.patch_page
    def verify_snapshot_before_patch(page,properties):
        assert (output/'staging_before.json').exists()
        assert (output/'staging_rollback_plan.json').exists()
        patch(page,properties)
    a.transport.patch_page=verify_snapshot_before_patch
    result=run_cycle(a,output)
    assert result['status']=='LOCAL_STAGING_HARNESS_PASS'
    assert result['remote_status']=='REMOTE_STAGING_NOT_RUN'
    assert result['updates']==3 and result['second_pass_semantic_delta']==0
    assert result['rollback']=='PASS' and a.transport.pages==original
    assert len(a.transport.patches)==6  # three apply, zero replay, three rollback
    assert len(result['artifact_hashes'])==6
    assert all(not(set(props)&{'Decision','Reviewer Note'}) for _,props in a.transport.patches)

@pytest.mark.parametrize('fault',['marker','target','schema','option'])
def test_preflight_failure_zero_writes(plan,tmp_path,fault):
    a=adapter(plan)
    if fault=='marker':a.transport.pages[UUID(PAGES[2]).hex]['marker']='PRODUCTION'
    if fault=='target':a.transport.pages[UUID(PAGES[2]).hex]['target_id']=str(uuid5(NS,'other'))
    if fault=='schema':a.transport.schema['Claim Text']['type']='title'
    if fault=='option':a.transport.schema['System Status']['options']=[]
    with pytest.raises(Blocked):run_cycle(a,tmp_path/'cycle')
    assert a.transport.patches==[]

def test_partial_apply_failure_rolls_back(plan,tmp_path):
    a=adapter(plan)
    original=deepcopy(a.transport.pages)
    patch=a.transport.patch_page
    calls=0
    def fail_once(page,properties):
        nonlocal calls
        calls+=1
        if calls==2:raise RuntimeError('simulated write failure')
        patch(page,properties)
    a.transport.patch_page=fail_once
    with pytest.raises(RuntimeError):run_cycle(a,tmp_path/'cycle')
    assert a.transport.pages==original
    report=json.loads((tmp_path/'cycle/staging_rollback_report.json').read_text())
    assert report['status']=='PASS'

def test_ambiguous_success_then_error_recovers(plan,tmp_path):
    a=adapter(plan)
    original=deepcopy(a.transport.pages)
    patch=a.transport.patch_page
    calls=0
    def ambiguous(page,properties):
        nonlocal calls
        calls+=1
        patch(page,properties)
        if calls==2:raise RuntimeError('response lost after apply')
    a.transport.patch_page=ambiguous
    with pytest.raises(RuntimeError):run_cycle(a,tmp_path/'cycle')
    assert a.transport.pages==original

def test_no_snapshot_blocks_write(plan):
    a=adapter(plan)
    with pytest.raises(Blocked):a.write(a.ids[0],plan['records'][0]['properties'],{})
    assert a.transport.patches==[]

def test_live_transport_requires_env_and_durable_snapshot(plan,monkeypatch):
    monkeypatch.delenv('V161_ENV',raising=False)
    with pytest.raises(Blocked):NotionStagingTransport(TARGET,PAGES,'test-placeholder',plan,[])
    monkeypatch.setenv('V161_ENV','STAGING')
    transport=NotionStagingTransport(TARGET,PAGES,'test-placeholder',plan,[])
    with pytest.raises(Blocked):transport.patch_page(PAGES[0],plan['records'][0]['properties'])

def test_concurrent_change_refuses_overwrite(plan,tmp_path):
    a=adapter(plan)
    a.preflight()
    a.before={p:a.read(p) for p in a.ids}
    expected=deepcopy(a.before[a.ids[0]]['properties'])
    a.transport.pages[a.ids[0]]['properties']['Run ID']={'rich_text':[]}
    with pytest.raises(Blocked):a.write(a.ids[0],plan['records'][0]['properties'],expected)
    assert a.transport.patches==[]
