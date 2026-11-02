import test from 'node:test';
import assert from 'node:assert/strict';
import {createHash} from 'node:crypto';
import {adaptRecords,verifySpans,loadNativeCase} from '../server/native-case.mjs';
import {sourceSegments,createGraphModel} from '../src/graph-model.js';

const sha=text=>createHash('sha256').update(text).digest('hex');
function fixture(){
  const text='Firm 🌱 emissions fell. A target was announced.';
  const source='Emissions were 10 in year one and 8 in year two.';
  const caseId='fixture', quote='emissions fell.';
  const start=Array.from(text.slice(0,text.indexOf(quote))).length;
  return {caseId,input:{generation_case_id:caseId,company_name:'Fixture',target_reporting_year:2020,task_id:'E1-6',task_title:'Fixture task',prompt_evidence:[{shown_in_prompt:true,evidence_id:'source1',retrieval_text:source,retrieval_text_hash:sha(source),source_year:2020,evidence_type:'csv_metric',metric:'Emissions'}]},
    generated:{generation_status:'success',generation_case_id:caseId,generated_text:text,generated_text_hash:sha(text)},
    dcRows:[{dc_id:'d1',dc_text:'Emissions declined.',generation_case_id:caseId,dc_provenance:[{generated_text_hash:sha(text),source_spans:[{start,end:start+quote.length,quote,match_status:'exact_unique',match_count:1}]}]},
      {dc_id:'d2',dc_text:'A target exists.',generation_case_id:caseId,dc_provenance:[{generated_text_hash:sha(text),source_spans:[{start:999,end:1001,quote:'missing',match_status:'unmatched',match_count:0}]}]}],
    ecRows:[{ec_id:'e1',ec_text:'Emissions were 10.',generation_case_id:caseId,evidence_card_ids:['source1']},{ec_id:'e2',ec_text:'Emissions were 8.',generation_case_id:caseId,evidence_card_ids:['source1']}],
    candidateRows:[{dc_claim_id:'d1',candidate_ec_ids:['e1','e2']},{dc_claim_id:'d2',candidate_ec_ids:[]}],
    supportRows:[{dc_claim_id:'d1',support_sets:[{support_type:'inferred',ec_claim_ids:['e1','e2']}]},{dc_claim_id:'d2',support_sets:[]}],
    diagnosisRows:[{dc_claim_id:'d2',unsupported_label:'unsupported_novelty',rationale:'No target in supplied evidence.'}],provenance:{runStatus:'incomplete'}};
}

test('preserves raw text, canonical claims, native identities, joint membership and saved diagnosis',()=>{
  const raw=fixture(), result=adaptRecords(raw);
  assert.equal(result.disclosure.text,raw.generated.generated_text);
  assert.equal(result.dcs[0].nativeId,'d1');assert.equal(result.dcs[0].text,'Emissions declined.');
  assert.deepEqual(result.dcs[0].sets[0].members,['ec1','ec2']);
  assert.equal(result.dcs[1].sourceStatus,'Unlocated');assert.deepEqual(result.dcs[1].spans,[]);
  assert.equal(result.dcs[1].rationale,raw.diagnosisRows[0].rationale);
  assert.equal(result.meta.runStatus,'incomplete');assert.equal(result.meta.assessmentStatus,'complete');
  assert.equal(result.disclosure.text.slice(result.dcs[0].spans[0].start,result.dcs[0].spans[0].end),'emissions fell.');
  const graph=createGraphModel(result);assert.equal(graph.sourceLinks.filter(l=>l.from==='text-dc2').length,0);
});
test('rejects absent judgments instead of silently producing unsupported outcomes',()=>{
  const raw=fixture();raw.supportRows.pop();assert.throws(()=>adaptRecords(raw),/Missing or foreign support/);
  const other=fixture();other.candidateRows.pop();assert.throws(()=>adaptRecords(other),/candidate assessment/);
});
test('rejects foreign and duplicate candidate references and non-candidate support',()=>{
  for(const ids of [['unknown'],['e1','e1']]){const raw=fixture();raw.candidateRows[0].candidate_ec_ids=ids;assert.throws(()=>adaptRecords(raw),/candidate references/);}
  const raw=fixture();raw.candidateRows[0].candidate_ec_ids=['e1'];assert.throws(()=>adaptRecords(raw),/non-candidate/);
});
test('rejects absent or contradictory diagnosis partition and changed source text',()=>{
  const raw=fixture();raw.diagnosisRows=[];assert.throws(()=>adaptRecords(raw),/Diagnoses/);
  const changed=fixture();changed.generated.generated_text+=' edited';assert.throws(()=>adaptRecords(changed),/text hash/);
  const foreign=fixture();foreign.ecRows[0].evidence_card_ids=['not-supplied'];assert.throws(()=>adaptRecords(foreign),/not supplied/);
});
test('ambiguous spans stay unlocated even when their quote is present',()=>{
  const text='same same';const m=verifySpans(text,[{hash:sha(text),source_spans:[{start:0,end:4,quote:'same',match_status:'exact_multiple',match_count:2}]}],'hash',sha(text));
  assert.equal(m.spans.length,0);assert.equal(m.unresolved.length,1);
  const mislabeled=verifySpans(text,[{hash:sha(text),source_spans:[{start:0,end:4,quote:'same',match_status:'exact_unique',match_count:1}]}],'hash',sha(text));
  assert.equal(mislabeled.spans.length,0,'Literal uniqueness is independently checked');
});
test('overlapping source spans preserve text exactly and retain all corresponding DCs',()=>{
  const text='ABC DEF GHI',segments=sourceSegments(text,0,text.length,[{id:'dc1',spans:[{start:0,end:7}]},{id:'dc2',spans:[{start:4,end:11}]}]);
  assert.equal(segments.map(s=>s.text).join(''),text);assert.deepEqual(segments.find(s=>s.text==='DEF').dcIds,['dc1','dc2']);
});
test('local adapter refuses an arbitrary filesystem path or unlisted case',async()=>{
  await assert.rejects(loadNativeCase('../../private'),/allowlist/);
});
