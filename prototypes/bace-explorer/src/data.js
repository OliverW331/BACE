// Synthetic UI fixtures, not saved BACE experimental results.
// Preserve the generated document independently from extracted/canonical DCs.
export const disclosure = {
  id: 'disclosure-2023',
  title: 'Environmental update',
  paragraphs: [
    {id:'p1', text:'During 2023, Scope 1 emissions fell by 20% compared with 2022. All manufacturing sites used renewable electricity, with renewable sources accounting for 60% of the group’s purchased electricity.'},
    {id:'p2', text:'The group has committed to achieving net-zero emissions by 2030. Our solar programme drove the reduction in Scope 2 emissions.'},
    {id:'p3', text:'No environmental fines were received during the reporting year.'},
  ],
};

// Exact character offsets into this synthetic source, not reconstructed DC text.
const locateSource = (paragraphId, quote) => {
  const paragraph = disclosure.paragraphs.find(p => p.id === paragraphId);
  const start = paragraph?.text.indexOf(quote) ?? -1;
  if (start < 0) throw new Error(`Missing source span in ${paragraphId}`);
  return {paragraphId, start, end:start + quote.length};
};

export const evidence = [
  { id:'ev1', label:'EV-01', title:'Emissions inventory', type:'Metrics', year:'2023', text:'Scope 1 emissions were 100,000 tCO2e in 2022 and 80,000 tCO2e in 2023. Scope 2 emissions decreased by 10% between 2022 and 2023.' },
  { id:'ev2', label:'EV-02', title:'Energy programme', type:'Report extract', year:'2023', text:'The pilot facility used renewable electricity in 2023. Renewable sources accounted for 60% of purchased electricity across the group. A solar programme was launched at the pilot facility in 2023.' },
  { id:'ev3', label:'EV-03', title:'Water data', type:'Metrics', year:'2023', text:'Group water withdrawal was 240,000 cubic metres in 2023.' },
  { id:'ev4', label:'EV-04', title:'Compliance statement', type:'Report extract', year:'2023', text:'The group received no environmental fines in 2023.' },
];
export const ecs = [
  { id:'ec1',label:'EC-01',short:'Scope 1 · 2022',text:'Scope 1 emissions were 100,000 tCO2e in 2022.',sources:['ev1'] },
  { id:'ec2',label:'EC-02',short:'Scope 1 · 2023',text:'Scope 1 emissions were 80,000 tCO2e in 2023.',sources:['ev1'] },
  { id:'ec3',label:'EC-03',short:'Pilot facility',text:'The pilot facility used renewable electricity in 2023.',sources:['ev2'] },
  { id:'ec4',label:'EC-04',short:'Renewable share',text:'Renewable sources accounted for 60% of purchased electricity across the group in 2023.',sources:['ev2'] },
  { id:'ec5',label:'EC-05',short:'Solar programme',text:'A solar programme was launched at the pilot facility in 2023.',sources:['ev2'] },
  { id:'ec6',label:'EC-06',short:'Scope 2 change',text:'Scope 2 emissions decreased by 10% between 2022 and 2023.',sources:['ev1'] },
  { id:'ec7',label:'EC-07',short:'Environmental fines',text:'The group received no environmental fines in 2023.',sources:['ev4'] },
  { id:'ec8',label:'EC-08',short:'Water withdrawal',text:'Group water withdrawal was 240,000 cubic metres in 2023.',sources:['ev3'] },
];
export const dcs = [
  {id:'dc1',label:'DC-01',short:'Lower Scope 1 emissions',text:'Scope 1 emissions decreased by 20% between 2022 and 2023.',source:locateSource('p1','Scope 1 emissions fell by 20% compared with 2022.'),candidates:['ec1','ec2','ec6'],sets:[{id:'a',type:'inferred',members:['ec1','ec2']}]},
  {id:'dc2',label:'DC-02',short:'Renewables at all sites',text:'All manufacturing sites used renewable electricity in 2023.',source:locateSource('p1','All manufacturing sites used renewable electricity'),candidates:['ec3','ec4','ec5'],sets:[],diagnosis:'Factual boundary distortion',rationale:'The evidence establishes renewable electricity use at the pilot facility, not at all manufacturing sites. The group-wide renewable share does not establish use at every site.'},
  {id:'dc3',label:'DC-03',short:'60% renewable electricity',text:'Renewable sources supplied 60% of the group’s purchased electricity in 2023.',source:locateSource('p1','renewable sources accounting for 60% of the group’s purchased electricity'),candidates:['ec3','ec4'],sets:[{id:'a',type:'direct',members:['ec4']}]},
  {id:'dc4',label:'DC-04',short:'A net-zero commitment',text:'The group committed to reach net-zero emissions by 2030.',source:locateSource('p2','The group has committed to achieving net-zero emissions by 2030.'),candidates:[],sets:[],diagnosis:'Unsupported novelty',rationale:'The supplied evidence contains no statement of a net-zero commitment or a 2030 target.'},
  {id:'dc5',label:'DC-05',short:'Solar drove the reduction',text:'The solar programme caused the reduction in Scope 2 emissions.',source:locateSource('p2','Our solar programme drove the reduction in Scope 2 emissions.'),candidates:['ec5','ec6'],sets:[],diagnosis:'Evidence conflation',rationale:'The evidence describes a solar programme and an emissions reduction separately. It does not establish that the programme caused the reduction.'},
  {id:'dc6',label:'DC-06',short:'No environmental fines',text:'The group received no environmental fines in 2023.',source:locateSource('p3','No environmental fines were received during the reporting year.'),candidates:['ec7'],sets:[{id:'a',type:'direct',members:['ec7']}]},
];

export function disclosureSegments(paragraph) {
  const segments = [];
  let cursor = 0;
  const claims = dcs.filter(dc => dc.source.paragraphId === paragraph.id)
    .sort((a, b) => a.source.start - b.source.start);
  for (const dc of claims) {
    const {start, end} = dc.source;
    if (start > cursor) segments.push({text:paragraph.text.slice(cursor, start)});
    segments.push({text:paragraph.text.slice(start, end), dcId:dc.id});
    cursor = end;
  }
  if (cursor < paragraph.text.length) segments.push({text:paragraph.text.slice(cursor)});
  return segments;
}
export const byId = Object.fromEntries([...dcs,...ecs,...evidence].map(item=>[item.id,item]));
export const outcome = dc => dc.sets.length ? (dc.sets.some(s=>s.type==='direct') ? 'Supported · Direct' : 'Supported · Inferred') : 'Unsupported';
export const relationships = dcs.flatMap(dc=>dc.candidates.map(ec=>({
  id:`${dc.id}-${ec}`,from:dc.id,to:ec,kind:dc.sets.some(s=>s.members.includes(ec))?'support':'candidate',
  sets:dc.sets.filter(s=>s.members.includes(ec)).map(s=>s.id),
})));
export const sourceLinks = [
  ...dcs.map(dc=>({id:`text-${dc.id}`,from:`text-${dc.id}`,to:dc.id,kind:'source'})),
  ...ecs.flatMap(ec=>ec.sources.map(ev=>({id:`${ec.id}-${ev}`,from:ec.id,to:ev,kind:'source'}))),
];
// Trace membership, not transitive graph closure: another DC's co-candidates
// must not light up merely because they share a connected disclosure claim.
export function traceSelection(id,setId=null){
  if(!id) return null;
  const nodeIds=new Set([id]),edgeIds=new Set();
  let matched;
  if(id.startsWith('dc')){
    const dc=byId[id],members=setId?dc.sets.find(s=>s.id===setId)?.members??[]:dc.candidates;
    matched=relationships.filter(r=>r.from===id&&members.includes(r.to));
  }else if(id.startsWith('ec')) matched=relationships.filter(r=>r.to===id);
  else{
    ecs.filter(ec=>ec.sources.includes(id)).forEach(ec=>nodeIds.add(ec.id));
    matched=relationships.filter(r=>nodeIds.has(r.to));
  }
  matched.forEach(r=>{nodeIds.add(r.from);nodeIds.add(r.to);edgeIds.add(r.id)});
  ecs.filter(ec=>nodeIds.has(ec.id)).forEach(ec=>ec.sources.forEach(ev=>{nodeIds.add(ev);edgeIds.add(`${ec.id}-${ev}`)}));
  dcs.filter(dc=>nodeIds.has(dc.id)).forEach(dc=>{nodeIds.add(`text-${dc.id}`);edgeIds.add(`text-${dc.id}`)});
  return{nodeIds,edgeIds};
}
