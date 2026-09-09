"""Isolated Kaggle NO_WRITE package, never touches the V15 deployment."""
from pathlib import Path
import json
import hashlib
import zipfile
import sys

ROOT=Path(__file__).resolve().parents[1]
DEST=ROOT/'.kaggle-deploy/v161-no-write'
INPUT=ROOT/'v16_migration/v161-inputs'
OUTPUT=ROOT/'v16_migration/baseline-v15-live'
report=json.loads((OUTPUT/'acceptance_checks.json').read_text(encoding='utf-8'))
assert report['gates']=={'update_count':70,'create_count':0,'missing_mapping_count':0,'mapping_collision_count':0,'human_field_write_count':0,'remote_writes':0,'schema_type_mismatch_count':0}
package=DEST/'package'
kernel=DEST/'kernel'
package.mkdir(parents=True,exist_ok=True)
kernel.mkdir(parents=True,exist_ok=True)
assets={}
for path in (ROOT/'src/kf_pilot/v16').glob('*.py'):
    assets[path.relative_to(ROOT).as_posix()]=path.read_bytes()
for name in ['src/kf_pilot/__init__.py','notebooks/30_migrate_v16.py','scripts/verify_v161_no_write.py']:
    assets[name]=(ROOT/name).read_bytes()
for name in ['v15_canonical_rows.json','current_notion_schema.json','live_knowledge_snapshot.json']:
    assets['inputs/'+name]=(INPUT/name).read_bytes()
assets['inputs/expected_local_plan.json']=(OUTPUT/'notion_typed_update_plan.json').read_bytes()
manifest={name:hashlib.sha256(value).hexdigest() for name,value in assets.items()}
if '--kernel-only' not in sys.argv:
    with zipfile.ZipFile(package/'v161-no-write.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for name,value in assets.items():archive.writestr(name,value)
        archive.writestr('sha256_manifest.json',json.dumps(manifest,sort_keys=True))
(package/'dataset-metadata.json').write_text(json.dumps({'title':'KF V161 No Write Baseline','id':'nguyeble/kf-v161-no-write-baseline','licenses':[{'name':'other'}]},indent=2),encoding='utf-8')
source='''from pathlib import Path
import hashlib, json, runpy, socket, sys, zipfile

# Network and credentials are not needed or used in this notebook.
def deny_network(*args, **kwargs):
    raise RuntimeError("NO_WRITE notebook forbids network access")
socket.socket.connect = deny_network
socket.create_connection = deny_network
input_root = Path('/kaggle/input')
manifests = list(input_root.rglob('sha256_manifest.json'))
if manifests:
    assert len(manifests) == 1, 'Ambiguous expanded dataset roots'
    root = manifests[0].parent
else:
    archives = list(input_root.rglob('v161-no-write.zip'))
    assert len(archives) == 1, 'Expected one expanded manifest or one archive'
    root = Path('/kaggle/working/v161')
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(archives[0]) as archive:
        for member in archive.infolist():
            target = (root/member.filename).resolve()
            assert root.resolve() in target.parents, 'Unsafe archive member'
        archive.extractall(root)
manifest = json.loads((root/'sha256_manifest.json').read_text(encoding='utf-8'))
for name, expected in manifest.items():
    target = (root/name).resolve()
    assert root.resolve() in target.parents, 'Unsafe manifest path'
    assert hashlib.sha256(target.read_bytes()).hexdigest() == expected, name
sys.path.insert(0,str(root/'src'))
inputs = root/'inputs'
output = Path('/kaggle/working/v16_migration/baseline-v15-live')
sys.argv = ['30_migrate_v16.py','--input',str(inputs/'v15_canonical_rows.json'),
    '--notion-schema',str(inputs/'current_notion_schema.json'),
    '--live-review-snapshot',str(inputs/'live_knowledge_snapshot.json'),
    '--output-dir',str(output),'--run-id','V16.1-BASELINE-NO-WRITE','--expected-count','70']
runpy.run_path(str(root/'notebooks/30_migrate_v16.py'),run_name='__main__')
sys.argv = ['verify','--root',str(root),'--inputs',str(inputs),'--output',str(output)]
runpy.run_path(str(root/'scripts/verify_v161_no_write.py'),run_name='__main__')
print((output/'prepublication_validation_report.json').read_text(encoding='utf-8'))
'''
notebook={'nbformat':4,'nbformat_minor':5,'metadata':{'kernelspec':{'display_name':'Python 3','language':'python','name':'python3'}},
    'cells':[{'cell_type':'markdown','id':'v161-description','metadata':{},'source':['# V16.1 — NO_WRITE\n70 real V15 rows; no secrets, HTTP, SQL or scheduler.']},
    {'cell_type':'code','id':'v161-bootstrap','metadata':{},'execution_count':None,'outputs':[],'source':source.splitlines(keepends=True)}]}
(kernel/'30_migrate_v16.ipynb').write_text(json.dumps(notebook,indent=1),encoding='utf-8')
(kernel/'kernel-metadata.json').write_text(json.dumps({'id':'nguyeble/kf-v161-migration-no-write','title':'KF V161 Migration NO WRITE',
    'code_file':'30_migrate_v16.ipynb','language':'python','kernel_type':'notebook','is_private':True,
    'enable_gpu':False,'enable_internet':False,'dataset_sources':['nguyeble/kf-v161-no-write-baseline'],
    'competition_sources':[],'kernel_sources':[],'model_sources':[]},indent=2),encoding='utf-8')
print(DEST)
