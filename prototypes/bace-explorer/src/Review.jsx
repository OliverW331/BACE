import {ArrowUpRight,ArrowLeft,ArrowRight,CaretDown,CheckCircle,WarningCircle,FileText,Graph,DotsThree,X,CaretDoubleDown,CaretDoubleUp} from '@phosphor-icons/react';

export function SourceRecord({item}) {
  if (!item.nativeId) return null;
  return <details className="record-details">
    <summary aria-label={`Source record for ${item.label}`} title="Source record"><DotsThree size={22}/></summary>
    <div><code>{item.nativeId}</code>
      {item.spans&&<p>{item.spans.length} verified spans · {item.sourceStatus}</p>}
      {item.sourceLabel&&<p>{item.sourceLabel}<br/>{item.sourceFile}{item.pageStart?` · Page ${item.pageStart}`:''}</p>}
      {item.type&&<p>{item.type} · {item.year}</p>}
    </div>
  </details>;
}

function EvidenceClaim({model,id,expanded,onToggle,onTrace,onReadEvidence}) {
  const ec=model.byId[id];
  return <article className={`review-ec${expanded?' expanded-ec':''}`} data-ec-id={id}>
    <div className="review-ec-header">
      {onToggle?<button className="ec-summary" aria-expanded={expanded} onClick={onToggle}>
        <strong>{ec.label}</strong>{!expanded&&<span>{ec.short}</span>}<CaretDown size={14}/>
      </button>:<strong>{ec.label}</strong>}
      <button className="icon-button trace-from" title={`Trace from ${ec.label}`} aria-label={`Trace from ${ec.label}`} onClick={()=>onTrace(id)}><Graph size={16}/></button>
    </div>
    {expanded&&<><p className="ec-full-text">{ec.text}</p>
      <div className="ec-sources">{ec.sources.map(source=><button key={source} onClick={()=>onReadEvidence(source)} title={`Read ${model.byId[source].title}`} aria-label={`Read ${model.byId[source].label} for ${ec.label}`}><FileText size={15}/>{model.byId[source].label}<ArrowUpRight size={12}/></button>)}<SourceRecord item={ec}/></div>
    </>}
  </article>;
}

export function Review({model,id,setId,expandedSetIds=[],onSet,onExpandAll,onFocusSet,onSelect,onClose,onReadEvidence,inspectedEC,onInspect,candidatesOpen,onCandidates,queue,onNavigate,passageIds=[]}) {
  if (!id) return null;
  const {byId,ecs,relationships}=model;
  const item=byId[id],isDC=id.startsWith('dc'),isEC=id.startsWith('ec');
  const position=queue.findIndex(dc=>dc.id===id);
  const evidenceClaim=(ec,expanded,onToggle)=> <EvidenceClaim key={ec} model={model} id={ec} expanded={expanded} onToggle={onToggle} onTrace={onSelect} onReadEvidence={onReadEvidence}/>;
  return <section className={`detail-panel${isDC&&!item.sets.length?' diagnosis-panel':''}`} aria-label="Selection details" data-testid="details" data-review-anchor={id}>
    <div className={`review-heading${passageIds.length>1?' passage-review-heading':''}`}>
      <div className="eyebrow">{passageIds.length>1?<div className="passage-switcher" role="group" aria-label="Disclosure claims in this passage">{passageIds.map(dc=><button key={dc} aria-label={`Review ${byId[dc].label}`} aria-pressed={dc===id} onClick={()=>onSelect(dc)}>{byId[dc].label}</button>)}</div>:<strong>{item.label}</strong>}{isDC&&<span className={`outcome ${item.sets.length?'supported':'unsupported'}`}>{item.sets.length?<CheckCircle size={15}/>:<WarningCircle size={15}/>}<span>{item.sets.length?'Supported':'Unsupported'}</span></span>}<SourceRecord item={item}/></div>
      <div className="review-navigation">{isDC&&<>
        <button className="icon-button" aria-label="Previous disclosure claim" title="Previous claim" disabled={position<=0} onClick={()=>onNavigate(-1)}><ArrowLeft size={17}/></button>
        <span aria-label={`Claim ${position+1} of ${queue.length}`}>{position+1} / {queue.length}</span>
        <button className="icon-button" aria-label="Next disclosure claim" title="Next claim" disabled={position<0||position>=queue.length-1} onClick={()=>onNavigate(1)}><ArrowRight size={17}/></button>
      </>}<button className="icon-button" onClick={onClose} aria-label="Clear selection" title="Close review"><X size={18}/></button></div>
    </div>
    <div className="detail-primary">
      <h2>{item.text}</h2>
      {isDC&&item.sourceStatus!=='Located'&&<p className="location-note">{item.sourceStatus}</p>}
      {!isDC&&!isEC&&<button className="read-evidence" onClick={()=>onReadEvidence(id)}><FileText size={16}/>Read evidence<ArrowUpRight size={13}/></button>}
      {isEC&&<div className="ec-sources">{item.sources.map(ev=><button key={ev} onClick={()=>onReadEvidence(ev)}><FileText size={15}/>{byId[ev].label}<ArrowUpRight size={12}/></button>)}</div>}
      {isDC&&!item.sets.length&&<div className="diagnosis-content"><div className="diagnosis-title"><WarningCircle size={17}/><h3>{item.diagnosis}</h3></div><p className="diagnosis-rationale">{item.rationale}</p></div>}
    </div>
    <div className="detail-secondary">
      {isDC?<>
        {item.sets.length>0&&<>
          {item.sets.length>1&&<div className="set-actions"><button onClick={()=>onExpandAll(expandedSetIds.length!==item.sets.length)} aria-label={expandedSetIds.length===item.sets.length?'Collapse all support sets':'Expand all support sets'}>
            {expandedSetIds.length===item.sets.length?<CaretDoubleUp size={15}/>:<CaretDoubleDown size={15}/>}{expandedSetIds.length===item.sets.length?'Collapse all':'Expand all'}
          </button></div>}
          <div className="set-list" aria-label="Alternative accepted support sets">{item.sets.map((set,index)=>{
            const expanded=expandedSetIds.includes(set.id);
            return <div key={set.id} className="support-group" data-set-id={set.id}>
              {index>0&&<div className="set-alternative">OR</div>}
              <div className="set-row"><button className={`set-button${setId===set.id?' selected-set':''}`} aria-expanded={expanded} aria-controls={`set-content-${id}-${set.id}`} onClick={()=>onSet(set.id)} data-testid={`set-${set.id}`}>
                <span className="set-name">Set {index+1}<span>{set.type}</span></span>
                <span className="set-members">{set.members.map((member,i)=><span key={member}>{i>0&&<small>AND</small>}<b>{byId[member].label}</b></span>)}</span><CaretDown size={15}/>
              </button><button className="icon-button set-focus" title={`Focus set ${index+1} in graph`} aria-label={`Focus set ${index+1} in graph`} aria-pressed={setId===set.id} onClick={()=>onFocusSet(set.id)}><Graph size={16}/></button></div>
              {expanded&&<div className="set-evidence" id={`set-content-${id}-${set.id}`} role="group" aria-label="Required together">{set.members.map((member,i)=><div key={member}>{i>0&&<div className="set-conjunction">AND</div>}{evidenceClaim(member,true)}</div>)}</div>}
            </div>;
          })}</div>
        </>}
        <div className="candidate-section">
          {item.sets.length>0?<button className="candidate-toggle" onClick={()=>onCandidates(!candidatesOpen)} aria-expanded={candidatesOpen}>Candidates<span>{item.candidates.length}</span><CaretDown size={14}/></button>:<div className="candidate-heading">Candidates<span>{item.candidates.length}</span></div>}
          {(candidatesOpen||!item.sets.length)&&<div className="candidate-list">{item.candidates.length?item.candidates.map(ec=>evidenceClaim(ec,inspectedEC===ec,()=>onInspect(inspectedEC===ec?null:ec))):<p className="empty-candidates">No candidates selected.</p>}</div>}
        </div>
      </>:<>
        <div className="section-label">{isEC?'Disclosure claims':'Evidence claims'}</div>
        <div className="related-list">{(isEC?relationships.filter(r=>r.to===id).map(r=>({...byId[r.from],relation:r.kind})):ecs.filter(ec=>ec.sources.includes(id))).map(related=><button key={related.id} onClick={()=>onSelect(related.id)}><strong>{related.label}</strong><span>{related.short}</span>{related.relation==='support'?<CheckCircle className="support-status" size={15} aria-label="Support-set membership"/>:<ArrowUpRight size={14}/>}<span className="sr-only">{related.relation==='candidate'?'Candidate relationship':''}</span></button>)}</div>
        {isEC&&!relationships.some(r=>r.to===id)&&<p className="subtle-note">Not selected as a candidate for any disclosure claim.</p>}
      </>}
    </div>
  </section>;
}
