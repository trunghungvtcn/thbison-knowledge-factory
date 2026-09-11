// Actual V1 planner source -> actual V2 synthetic writer. No external services.
import assert from 'node:assert/strict';
import {fileURLToPath} from 'node:url';
import {mkdtempSync,readFileSync,writeFileSync,mkdirSync} from 'node:fs';
import {tmpdir} from 'node:os';
import {join,resolve} from 'node:path';
process.env.THBISON_DATA_DIR=mkdtempSync(join(tmpdir(),'thbison-preview-'));
process.env.THBISON_MODE='MOCK';
process.env.THBISON_ROOT=fileURLToPath(new URL('../modules/vendor1/',import.meta.url));
process.env.THBISON_CLOCK_NOW='2030-01-01T00:00:00Z';
const {handlePlanningHttp}=await import('../modules/vendor1/src/planning/http.ts');
const {generateSyntheticArticle}=await import('../modules/vendor2/src/lib/content-os/writer.ts');
const {checkArticle,checkBundle}=await import('../modules/vendor2/src/lib/content-os/gate.ts');
const {hashWithout}=await import('../modules/vendor2/src/lib/content-os/hash.ts');
const fixture=JSON.parse(readFileSync(new URL('../modules/vendor2/src/lib/content-os/kit-fixtures.json',import.meta.url),'utf8'));
const request=JSON.parse(readFileSync(new URL('../modules/vendor1/vendor_kit/contracts/examples/ResearchRequest.json',import.meta.url),'utf8'));
request.budget.deadline_at='2030-01-01T00:05:00Z';
request.seeds=['pa lăng xích kéo tay'];request.existing_pages=[];
const headers={'authorization':'Bearer thbison-test-token-aaaaaaaa','content-type':'application/json','x-contract-version':'1.0.0','idempotency-key':'master-preview-001'};
const admitted=await handlePlanningHttp(new Request('http://localhost/v1/planning/jobs',{method:'POST',headers,body:JSON.stringify(request)}));
assert.equal(admitted.status,202);const job=await admitted.json();let output;
for(let n=0;n<100;n++){
 const res=await handlePlanningHttp(new Request(`http://localhost/v1/planning/jobs/${job.job_id}`,{headers}));const state=await res.json();
 if(state.status==='SUCCEEDED'){
  const out=await handlePlanningHttp(new Request(`http://localhost/v1/planning/jobs/${job.job_id}/output`,{headers}));assert.equal(out.status,200);output=await out.json();break;
 }
 assert(!['FAILED','CANCELLED','BUDGET_EXHAUSTED'].includes(state.status),JSON.stringify(state));
 await new Promise(r=>setTimeout(r,20));
}
assert(output,'planner timeout');
const evidence=structuredClone(fixture.evidence);
evidence.project_id=output.brief.project_id;evidence.data_class='TEST_ONLY';
evidence.snapshot_sha256=hashWithout(evidence,'snapshot_sha256');checkBundle(evidence);
const article=generateSyntheticArticle(output.brief,evidence,'test-master-article',1);checkArticle(article,evidence);
assert.equal(article.brief_id,output.brief.brief_id);assert.equal(article.brief_revision,output.brief.brief_revision);
const dir=resolve(process.argv[2]||'evidence/integration');mkdirSync(dir,{recursive:true});
for(const [name,value] of Object.entries({planning:output,brief:output.brief,evidence,article}))writeFileSync(join(dir,`${name}.json`),JSON.stringify(value,null,2));
writeFileSync(join(dir,'scope.json'),JSON.stringify({result:'PASS',execution:'in-process vendor source',planning:'V1 source, mock SEO',writing:'V2 source, synthetic writer',knowledge:'TEST_ONLY fixture',database_integration:false,runtime_integration:false,cms_integration:false,public_effects:0},null,2));
console.log('V1_TO_V2_SYNTHETIC_PREVIEW_PASS',dir);
