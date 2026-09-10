#!/usr/bin/env python3
"""Bounded core checks; never claims UI, DB or service E2E."""
from pathlib import Path
import subprocess,sys,json,os,hashlib
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'evidence/core-run';OUT.mkdir(parents=True,exist_ok=True)
steps=[('v1-core',['node','--experimental-strip-types','--test','src/planning/jobs.test.ts'],ROOT/'modules/vendor1'),('v2-core',['node','--experimental-strip-types','--import','./tests/register-ts-ext.mjs','--test',*[str(p.relative_to(ROOT/'modules/vendor2')) for p in sorted((ROOT/'modules/vendor2/src/lib/content-os').glob('*.test.ts'))]],ROOT/'modules/vendor2')]
for n,kit in [(1,'vendor_kit'),(2,'vendor-kit')]:steps.append((f'v{n}-contracts',[sys.executable,'-m','pytest','tests/test_contracts.py','-q',f'--junitxml={OUT}/v{n}-contracts.xml'],ROOT/f'modules/vendor{n}'/kit))
steps.append(('v1-v2-preview',['node','--experimental-strip-types','--import','./modules/vendor2/tests/register-ts-ext.mjs','integration/v1-v2-preview.mjs',str(OUT/'preview')],ROOT))
results=[]
shared_mismatches=[]
for canonical in (ROOT/'contracts/schemas').glob('*.json'):
    for candidate in (ROOT/'modules').rglob('schemas/'+canonical.name):
        if candidate.read_bytes()!=canonical.read_bytes():
            shared_mismatches.append(str(candidate.relative_to(ROOT)))
results.append({'step':'shared-schema-bytes','exit':int(bool(shared_mismatches)),'mismatches':shared_mismatches})
for name,cmd,cwd in steps:
 try:
  p=subprocess.run(cmd,cwd=cwd,capture_output=True,text=True,timeout=90)
  (OUT/f'{name}.log').write_text(p.stdout+p.stderr);rc=p.returncode
 except subprocess.TimeoutExpired:
  rc=124;(OUT/f'{name}.log').write_text('TIMEOUT 90s; not PASS')
 results.append({'step':name,'exit':rc,'command':cmd,'cwd':str(cwd.relative_to(ROOT))});print(name,rc,flush=True)
# Validate the actual handoff payloads, not just static examples.
try:
 from jsonschema import Draft202012Validator,FormatChecker
 schema_results={}
 for filename,name in [('planning','PlanningOutput'),('brief','ContentBrief'),('evidence','EvidenceBundle'),('article','ArticlePackage')]:
  data=json.loads((OUT/'preview'/f'{filename}.json').read_text());schema=json.loads((ROOT/'contracts/schemas'/f'{name}.json').read_text())
  # Resolve sibling refs with a local registry only.
  from referencing import Registry,Resource
  base='https://contracts.invalid/thbison/1.0.0/'
  registry=Registry().with_resources((base+p.name,Resource.from_contents(json.loads(p.read_text()))) for p in (ROOT/'contracts/schemas').glob('*.json'))
  schema['$id']=base+name+'.json'
  errors=list(Draft202012Validator(schema,registry=registry,format_checker=FormatChecker()).iter_errors(data));schema_results[name]=[e.message for e in errors]
 (OUT/'boundary-validation.json').write_text(json.dumps(schema_results,indent=2))
 results.append({'step':'actual-payload-schema','exit':int(any(schema_results.values()))})
except Exception as exc:
 results.append({'step':'actual-payload-schema','exit':1,'reason':str(exc)})
(OUT/'RESULTS.json').write_text(json.dumps({'checks':results,'scope':'core+in-process preview only','actual_service_e2e':False,'production_ready':False},indent=2))
sys.exit(int(any(x['exit'] for x in results)))
