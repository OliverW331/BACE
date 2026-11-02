import * as demo from './data.js';

export const demoCase = {
  meta:{id:'demo',kind:'demo',company:'Example Manufacturing',year:'2023',taskTitle:'Environmental update',badge:'Illustrative data'},
  disclosure:{...demo.disclosure,text:demo.disclosure.paragraphs.map(p=>p.text).join('\n\n')},
  dcs:demo.dcs.map(dc=>{
    const index=demo.disclosure.paragraphs.findIndex(p=>p.id===dc.source.paragraphId);
    const offset=demo.disclosure.paragraphs.slice(0,index).reduce((n,p)=>n+p.text.length+2,0);
    return {...dc,assessmentStatus:'complete',sourceStatus:'Located',spans:[{start:offset+dc.source.start,end:offset+dc.source.end}],unresolvedSpans:[]};
  }),ecs:demo.ecs,evidence:demo.evidence,
};

export const outcome = dc => dc.assessmentStatus!=='complete' ? 'Assessment unavailable' : dc.sets.length ? (dc.sets.some(s=>s.type==='direct')?'Supported · Direct':'Supported · Inferred') : 'Unsupported';

export function createGraphModel(data){
  const {dcs,ecs,evidence}=data,byId=Object.fromEntries([...dcs,...ecs,...evidence].map(item=>[item.id,item]));
  const relationships=dcs.flatMap(dc=>dc.candidates.map(ec=>({id:`${dc.id}-${ec}`,from:dc.id,to:ec,kind:dc.sets.some(s=>s.members.includes(ec))?'support':'candidate'})));
  const sourceLinks=[...dcs.filter(dc=>dc.spans.length).map(dc=>({id:`text-${dc.id}`,from:`text-${dc.id}`,to:dc.id,kind:'source'})),...ecs.flatMap(ec=>ec.sources.map(ev=>({id:`${ec.id}-${ev}`,from:ec.id,to:ev,kind:'source'})))];
  function traceSelection(id,setId=null){
    if(!id||!byId[id])return null;
    const nodeIds=new Set([id]),edgeIds=new Set();let matched;
    if(id.startsWith('dc')){
      const dc=byId[id],members=setId?dc.sets.find(s=>s.id===setId)?.members??[]:dc.candidates;
      matched=relationships.filter(r=>r.from===id&&members.includes(r.to));
    }else if(id.startsWith('ec'))matched=relationships.filter(r=>r.to===id);
    else{ecs.filter(ec=>ec.sources.includes(id)).forEach(ec=>nodeIds.add(ec.id));matched=relationships.filter(r=>nodeIds.has(r.to));}
    matched.forEach(r=>{nodeIds.add(r.from);nodeIds.add(r.to);edgeIds.add(r.id)});
    ecs.filter(ec=>nodeIds.has(ec.id)).forEach(ec=>ec.sources.forEach(ev=>{nodeIds.add(ev);edgeIds.add(`${ec.id}-${ev}`)}));
    dcs.filter(dc=>nodeIds.has(dc.id)&&dc.spans.length).forEach(dc=>{nodeIds.add(`text-${dc.id}`);edgeIds.add(`text-${dc.id}`)});
    return {nodeIds,edgeIds};
  }
  function traceClaims(ids){
    const traces=ids.map(id=>traceSelection(id)).filter(Boolean);
    return {nodeIds:new Set(traces.flatMap(trace=>[...trace.nodeIds])),edgeIds:new Set(traces.flatMap(trace=>[...trace.edgeIds]))};
  }
  return {...data,byId,relationships,sourceLinks,allEdges:[...sourceLinks,...relationships],traceSelection,traceClaims};
}

// Split overlapping spans into disjoint inline fragments. Each fragment retains
// every matching DC, so no claim text is duplicated and no arbitrary DC wins.
export function sourceSegments(text,start,end,dcs){
  const overlaps=dcs.flatMap(dc=>dc.spans.filter(s=>s.start<end&&s.end>start).map(s=>({id:dc.id,start:Math.max(start,s.start),end:Math.min(end,s.end)})));
  const points=[...new Set([start,end,...overlaps.flatMap(s=>[s.start,s.end])])].sort((a,b)=>a-b);
  return points.slice(0,-1).map((a,i)=>({start:a,end:points[i+1],text:text.slice(a,points[i+1]),dcIds:[...new Set(overlaps.filter(s=>s.start<=a&&s.end>=points[i+1]).map(s=>s.id))]}));
}
