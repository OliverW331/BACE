import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {CASE_ID,loadNativeCase} from '../server/native-case.mjs';

const data=await loadNativeCase(CASE_ID);
const code={};
for(const path of ['server/native-case.mjs','src/graph-model.js'])code[path]=createHash('sha256').update(await readFile(path)).digest('hex');
const report={verifiedAt:new Date().toISOString(),caseId:data.meta.id,company:data.meta.company,year:data.meta.year,
  counts:data.meta.counts,examples:data.meta.examples,codeSha256:code,provenance:data.provenance,
  rules:{counts:'Counts over the full canonical case inventories; support membership counts distinct DC–EC pairs, not the sum of set sizes.',
    sourceMapping:'Use saved exact_unique spans only, verify their quote at saved Unicode code-point offsets, then convert to browser UTF-16 offsets.',
    outcomes:'Direct when any saved set is direct; inferred when sets exist and all are inferred; unsupported only for a present completed assessment with an empty set list.'}};
await mkdir('qa',{recursive:true});await writeFile('qa/native-case-audit.json',JSON.stringify(report,null,2)+'\n');
console.log(JSON.stringify({caseId:report.caseId,counts:report.counts,verifiedFiles:report.provenance.files.length,report:'qa/native-case-audit.json'},null,2));
