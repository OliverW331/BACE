import {readFile, stat} from 'node:fs/promises';
import {createReadStream} from 'node:fs';
import {createHash} from 'node:crypto';
import {createInterface} from 'node:readline';
import {resolve, relative} from 'node:path';
import {fileURLToPath} from 'node:url';

export const BACE_ROOT = resolve(fileURLToPath(new URL('../../../BACE/', import.meta.url)));
export const CASE_ID = 'w2__text_embedding_3_large__stratified_by_evidence_type_n10__intesa_sanpaolo__2020__e1_6_ghg_emissions';
export const CATALOG = [{id:CASE_ID, label:'Intesa Sanpaolo · 2020 · E1-6', run:'main_v1'}];
const STAGES = ['generation','direct','integrated','atomic','dedup','candidates','support','diagnosis'];
const LABELS = new Set(['non_disclosure_statement','contradiction','evidence_conflation','factual_boundary_distortion','inferential_inflation','unsupported_novelty']);
const sha = bytes => createHash('sha256').update(bytes).digest('hex');
const insist = (value, message) => {if (!value) throw new Error(message);};
const title = s => s.replaceAll('_',' ').replace(/^./,c=>c.toUpperCase());
// Display excerpts remove repeated metadata, while `text` stays verbatim.
function excerpt(text,company){
  return text.replace(/^According to [\s\S]*? record, /,'').replace(/^For the \d{4} reporting year, /,'')
    .replaceAll(company+'’s ','').replaceAll(company+"'s ",'').replaceAll(company+' ','')
    .replace(/^\d{4} /,'').replace(/greenhouse gas emissions/g,'GHG emissions');
}
const index = (rows,key) => {const map=new Map(rows.map(r=>[r[key],r]));insist(map.size===rows.length,`Duplicate ${key}`);return map;};
const same = (a,b) => a.size===b.size && [...a].every(x=>b.has(x));
const stable = x => JSON.stringify(x && typeof x==='object' ? (Array.isArray(x) ? x.map(v=>JSON.parse(stable(v))) : Object.fromEntries(Object.keys(x).sort().map(k=>[k,JSON.parse(stable(x[k]))]))) : x);

// Saved offsets count Unicode code points; browser offsets count UTF-16 units.
export function verifySpans(text, provenance, hashField, expectedHash) {
  const characters=Array.from(text), spans=[], unresolved=[];
  for (const occurrence of provenance ?? []) {
    insist(occurrence[hashField]===expectedHash, 'Source provenance hash mismatch');
    for (const item of occurrence.source_spans ?? []) {
      const {start,end,quote,match_status:status}=item;
      const valid=status==='exact_unique' && item.match_count===1 && Number.isInteger(start) && Number.isInteger(end) && start>=0 && end>start && end<=characters.length && characters.slice(start,end).join('')===quote && text.indexOf(quote)===text.lastIndexOf(quote);
      if (!valid) {unresolved.push({quote,status:status??'missing',reason:'No verified unique source location'});continue;}
      spans.push({start:characters.slice(0,start).join('').length,end:characters.slice(0,end).join('').length,quote,nativeStart:start,nativeEnd:end,status});
    }
  }
  return {spans:[...new Map(spans.map(s=>[`${s.start}:${s.end}`,s])).values()].sort((a,b)=>a.start-b.start),unresolved};
}

export function adaptRecords({caseId, input, generated, dcRows, ecRows, candidateRows, supportRows, diagnosisRows, provenance}) {
  insist(generated.generation_status==='success','Generation is not complete');
  insist(input.generation_case_id===caseId && generated.generation_case_id===caseId,'Case identity mismatch');
  insist(sha(generated.generated_text)===generated.generated_text_hash,'Generated text hash mismatch');
  const dcIndex=index(dcRows,'dc_id'), ecIndex=index(ecRows,'ec_id');
  insist(dcRows.length && ecRows.length,'Empty claim inventory');
  for(const r of [...dcRows,...ecRows]) insist(r.generation_case_id===caseId,'Cross-case claim');
  const candidates=index(candidateRows,'dc_claim_id'),supports=index(supportRows,'dc_claim_id'),diagnoses=index(diagnosisRows,'dc_claim_id');
  insist(same(new Set(dcIndex.keys()),new Set(candidates.keys())),'Missing or foreign candidate assessment');
  insist(same(new Set(dcIndex.keys()),new Set(supports.keys())),'Missing or foreign support assessment');
  const unsupported=new Set();
  for(const dc of dcRows){
    const ids=candidates.get(dc.dc_id).candidate_ec_ids, sets=supports.get(dc.dc_id).support_sets;
    insist(Array.isArray(ids) && new Set(ids).size===ids.length && ids.every(id=>ecIndex.has(id)),'Invalid candidate references');
    insist(Array.isArray(sets),'Missing support sets');
    if(!sets.length) unsupported.add(dc.dc_id);
    for(const set of sets){
      insist(['direct','inferred'].includes(set.support_type),'Unknown support type');
      insist(Array.isArray(set.ec_claim_ids) && set.ec_claim_ids.length && new Set(set.ec_claim_ids).size===set.ec_claim_ids.length && set.ec_claim_ids.every(id=>ids.includes(id)),'Support set includes a non-candidate or duplicate EC');
    }
  }
  insist(same(unsupported,new Set(diagnoses.keys())),'Diagnoses do not match the unsupported DC inventory');
  for(const d of diagnosisRows) insist(LABELS.has(d.unsupported_label) && typeof d.rationale==='string' && d.rationale.trim(),'Invalid diagnosis');
  const cards=input.prompt_evidence.filter(c=>c.shown_in_prompt===true);
  const cardIndex=index(cards,'evidence_id');
  for(const c of cards) insist(sha(c.retrieval_text)===c.retrieval_text_hash,'Evidence text hash mismatch');
  const evAliases=new Map(cards.map((c,i)=>[c.evidence_id,`ev${i+1}`]));
  const ecAliases=new Map(ecRows.map((c,i)=>[c.ec_id,`ec${i+1}`]));
  const dcs=dcRows.map(row=>({...row,mapping:verifySpans(generated.generated_text,row.dc_provenance,'generated_text_hash',generated.generated_text_hash)}))
    .sort((a,b)=>(a.mapping.spans[0]?.start??Infinity)-(b.mapping.spans[0]?.start??Infinity)||a.dc_id.localeCompare(b.dc_id))
    .map((row,i)=>{
      const nativeSets=supports.get(row.dc_id).support_sets, diagnosis=diagnoses.get(row.dc_id);
      return {id:`dc${i+1}`,label:`DC-${String(i+1).padStart(2,'0')}`,nativeId:row.dc_id,text:row.dc_text,short:excerpt(row.dc_text,input.company_name),
        spans:row.mapping.spans,unresolvedSpans:row.mapping.unresolved,
        sourceStatus:!row.mapping.spans.length ? 'Unlocated' : row.mapping.unresolved.length ? 'Partially located' : 'Located',
        candidates:candidates.get(row.dc_id).candidate_ec_ids.map(id=>ecAliases.get(id)),assessmentStatus:'complete',
        sets:nativeSets.map((s,j)=>({id:String(j+1),type:s.support_type,members:s.ec_claim_ids.map(id=>ecAliases.get(id)),recordIndex:j})),
        diagnosis:diagnosis?title(diagnosis.unsupported_label):null,diagnosisCode:diagnosis?.unsupported_label??null,rationale:diagnosis?.rationale??null};
    });
  const ecs=ecRows.map((row,i)=>{
    insist(Array.isArray(row.evidence_card_ids) && row.evidence_card_ids.length && row.evidence_card_ids.every(id=>cardIndex.has(id)),'EC refers to evidence not supplied to generation');
    const sourceSpans=[];
    for(const p of row.ec_provenance??[]){
      const card=cardIndex.get(p.evidence_id);insist(card,'Unknown EC provenance source');
      const mapping=verifySpans(card.retrieval_text,[p],'retrieval_text_hash',card.retrieval_text_hash);
      sourceSpans.push({source:evAliases.get(p.evidence_id),...mapping});
    }
    const quote=row.ec_text.match(/[“"]([^”"]+)[”"] indicator/),value=row.ec_text.match(/ was ([^]+?) under ESG/);
    return {id:`ec${i+1}`,label:`EC-${String(i+1).padStart(2,'0')}`,nativeId:row.ec_id,text:row.ec_text,
      short:quote?quote[1].replace(/greenhouse gas emissions/g,'GHG emissions'):excerpt(row.ec_text,input.company_name),
      previewValue:value?.[1]??null,sources:row.evidence_card_ids.map(id=>evAliases.get(id)),sourceSpans};
  });
  const evidence=cards.map((card,i)=>({id:`ev${i+1}`,label:`EV-${String(i+1).padStart(2,'0')}`,nativeId:card.evidence_id,
    title:card.metric||card.source_label,type:title(card.evidence_type),year:String(card.source_year),text:card.retrieval_text,
    sourceLabel:card.source_label,sourceFile:card.source_file,pageStart:card.page_start,pageEnd:card.page_end,promptLabel:card.prompt_label,textHash:card.retrieval_text_hash}));
  const counts={dcs:dcs.length,ecs:ecs.length,evidence:evidence.length,candidates:dcs.reduce((n,d)=>n+d.candidates.length,0),
    direct:dcs.filter(d=>d.sets.some(s=>s.type==='direct')).length,inferred:dcs.filter(d=>d.sets.length&&!d.sets.some(s=>s.type==='direct')).length,
    unsupported:dcs.filter(d=>!d.sets.length).length,supportSets:dcs.reduce((n,d)=>n+d.sets.length,0),
    supportMemberships:dcs.reduce((n,d)=>n+new Set(d.sets.flatMap(s=>s.members)).size,0),
    locatedDCs:dcs.filter(d=>d.spans.length).length,unresolvedSpans:dcs.reduce((n,d)=>n+d.unresolvedSpans.length,0)};
  return {schemaVersion:'bace_explorer_case_v1',meta:{id:caseId,kind:'native',company:input.company_name,year:String(input.target_reporting_year),taskId:input.task_id,taskTitle:input.task_title,runId:generated.run_id,badge:'Saved BACE run',assessmentStatus:'complete',runStatus:provenance.runStatus,counts,
    examples:{joint:dcs.find(d=>d.sets.length&&d.sets.every(s=>s.members.length>1))?.id,diagnosis:dcs.find(d=>d.diagnosisCode&&d.diagnosisCode!=='non_disclosure_statement')?.id,inferred:dcs.find(d=>d.sets.length&&d.sets.every(s=>s.type==='inferred'))?.id}},
    disclosure:{id:generated.generation_output_id,title:input.task_title,text:generated.generated_text,textHash:generated.generated_text_hash},dcs,ecs,evidence,provenance};
}

export async function loadNativeCase(caseId, {root=BACE_ROOT}={}) {
  insist(CATALOG.some(c=>c.id===caseId),'Case is not in the local allowlist');
  const run=resolve(root,'results/main_v1'), base=resolve(run,'cases',caseId), sources=[];
  async function bytes(path,expected){
    const before=await stat(path), raw=await readFile(path), digest=sha(raw), after=await stat(path);
    insist(before.mtimeMs===after.mtimeMs && before.size===after.size,'Source changed during read');
    if(expected) insist(digest===expected,`Saved receipt hash mismatch: ${relative(root,path)}`);
    sources.push({path:relative(root,path),sha256:digest,size:after.size,mtimeMs:after.mtimeMs,receiptVerified:Boolean(expected)});return raw;
  }
  const json=async (p,e)=>JSON.parse(await bytes(p,e));
  const rows=async (p,e)=>(await bytes(p,e)).toString('utf8').split(/\r?\n/).filter(s=>s.trim()).map(JSON.parse);
  const manifest=await json(resolve(run,'manifest.json')), execution=await json(resolve(run,'execution_status.json'));
  insist(!execution.active_cases?.length&&!['running','finalizing'].includes(execution.status),'Run is active; retry after saved artifacts are stable');
  insist(manifest.case_ids.includes(caseId),'Case absent from run manifest');
  await bytes(resolve(root,'config/freeze.json'),manifest.freeze_sha256);
  const state=await json(resolve(base,'state.json'));
  insist(state.status==='complete'&&STAGES.every(s=>state.stages[s]),'Case stages are not complete');
  const stageRows=async (stage,name)=>{
    const path=resolve(base,name),expected=state.stages[stage].artifacts[relative(root,path).replaceAll('\\','/')];
    insist(expected,`Missing ${stage} receipt`);return rows(path,expected);
  };
  const generations=await stageRows('generation','generation/generated_disclosures.jsonl');
  insist(generations.length===1,'Expected one saved generation');const generated=generations[0];
  const inputs=await rows(resolve(base,'inputs/generation_cases.jsonl'),generated.generation_cases_sha256);
  insist(inputs.length===1,'Expected one case input');
  // Check the selected input against the globally hash-bound frozen input, read only.
  const globalPath=resolve(root,'evidence/inputs/generation_cases.jsonl'), before=await stat(globalPath), hash=createHash('sha256');
  const stream=createReadStream(globalPath);stream.on('data',chunk=>hash.update(chunk));let matches=0;
  for await(const line of createInterface({input:stream,crlfDelay:Infinity})){
    if(line.includes(caseId)){const r=JSON.parse(line);if(r.generation_case_id===caseId){matches++;insist(stable(r)===stable(inputs[0]),'Case input differs from frozen generation input');}}
  }
  const digest=hash.digest('hex'),after=await stat(globalPath);
  insist(matches===1 && digest===manifest.generation_input_sha256 && before.size===after.size && before.mtimeMs===after.mtimeMs,'Frozen input verification failed');
  sources.push({path:relative(root,globalPath),sha256:digest,size:after.size,mtimeMs:after.mtimeMs,receiptVerified:true});
  const records={caseId,input:inputs[0],generated,
    dcRows:await stageRows('dedup','bace/dedup/dc_claims.jsonl'),ecRows:await stageRows('dedup','bace/dedup/ec_claims.jsonl'),
    candidateRows:await stageRows('candidates','bace/candidates/dc_candidate_ecs.jsonl'),supportRows:await stageRows('support','bace/support/dc_support_sets.jsonl'),
    diagnosisRows:await stageRows('diagnosis','bace/diagnosis/dc_unsupported_diagnoses.jsonl'),
    provenance:{runStatus:execution.status,caseStatus:state.status,stages:STAGES,files:sources,scope:'Consumed stage artifacts and text hashes verified; saved automated assessments, not human validation.'}};
  const data=adaptRecords(records);
  for(const file of sources){const now=await stat(resolve(root,file.path));insist(now.size===file.size&&now.mtimeMs===file.mtimeMs,'Source changed during adaptation');}
  return data;
}

export function nativeCasePlugin(){
  let cached;
  const mount=server=>{server.middlewares.use(async(req,res,next)=>{
    const url=new URL(req.url,'http://localhost');
    if(!url.pathname.startsWith('/api/bace/'))return next();
    res.setHeader('Content-Type','application/json');res.setHeader('Cache-Control','no-store');
    const peer=req.socket.remoteAddress;
    if(!['127.0.0.1','::1','::ffff:127.0.0.1'].includes(peer)){res.statusCode=403;return res.end(JSON.stringify({error:'Saved cases are available only through the local preview.'}));}
    if(req.method!=='GET'){res.statusCode=405;return res.end(JSON.stringify({error:'Read-only endpoint'}));}
    try{
      if(url.pathname==='/api/bace/cases')return res.end(JSON.stringify({cases:CATALOG}));
      const id=decodeURIComponent(url.pathname.slice('/api/bace/cases/'.length));
      if(!CATALOG.some(c=>c.id===id)){res.statusCode=404;return res.end(JSON.stringify({error:'Unknown saved case'}));}
      if(cached){for(const f of cached.provenance.files){const s=await stat(resolve(BACE_ROOT,f.path));if(s.size!==f.size||s.mtimeMs!==f.mtimeMs){cached=null;break;}}}
      cached??=await loadNativeCase(id);res.end(JSON.stringify(cached));
    }catch(error){cached=null;res.statusCode=422;res.end(JSON.stringify({error:error.message}));}
  });};
  return {name:'local-bace-saved-case',configureServer:mount,configurePreviewServer:mount};
}
