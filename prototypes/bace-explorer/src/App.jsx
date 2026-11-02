import {useState,useRef,useLayoutEffect,useEffect,useCallback,useMemo} from 'react';
import {linkHorizontal} from 'd3-shape';
import {Graph,ArrowCounterClockwise,MagnifyingGlassPlus,MagnifyingGlassMinus,ArrowsOutSimple,Info,WarningCircle,X,PushPin,CheckCircle,ArrowUpRight,ArrowDown,FadersHorizontal} from '@phosphor-icons/react';
import {demoCase,createGraphModel,outcome} from './graph-model';
import {Document} from './Document';
import {Review} from './Review';

const route=linkHorizontal().x(d=>d[0]).y(d=>d[1]);

export function App(){
  const [catalog,setCatalog]=useState([]),[mode,setMode]=useState(new URLSearchParams(location.search).get('case')==='demo'?'demo':'native');
  const [data,setData]=useState(demoCase),[loading,setLoading]=useState(false),[error,setError]=useState('');
  useEffect(()=>{const abort=new AbortController();fetch('/api/bace/cases',{signal:abort.signal}).then(r=>{if(!r.ok)throw Error('Saved cases are available in the local preview.');return r.json()}).then(r=>setCatalog(r.cases)).catch(e=>{if(e.name!=='AbortError')setError(e.message)});return()=>abort.abort()},[]);
  useEffect(()=>{
    if(mode==='demo'){setData(demoCase);setLoading(false);setError('');return;}
    if(!catalog.length)return;
    const abort=new AbortController();setLoading(true);setError('');
    fetch(`/api/bace/cases/${encodeURIComponent(catalog[0].id)}`,{signal:abort.signal}).then(async r=>{const body=await r.json();if(!r.ok)throw Error(body.error||'Unable to load the saved case.');return body}).then(r=>{setData(r);setLoading(false)}).catch(e=>{if(e.name!=='AbortError'){setError(e.message);setLoading(false)}});
    return()=>abort.abort();
  },[mode,catalog]);
  const picker=<select aria-label="Choose case" value={mode} onChange={e=>setMode(e.target.value)}><option value="native">{catalog[0]?.label??'Saved BACE case'}</option><option value="demo">Illustrative example</option></select>;
  return <Explorer key={data.meta.id} data={data} picker={picker} loadNotice={loading?'Loading and verifying saved artifacts…':error} loadError={Boolean(error)}/>;
}

function Explorer({data,picker,loadNotice,loadError}){
  const model=useMemo(()=>createGraphModel(data),[data]);
  const {dcs,ecs,evidence,disclosure,byId,allEdges,traceSelection,traceClaims,meta}=model;
  const native=meta.kind==='native';
  const [selected,setSelected]=useState(null),[hovered,setHovered]=useState(null),[setId,setSetId]=useState(null),[expandedSetIds,setExpandedSetIds]=useState([]);
  const [supportOnly,setSupportOnly]=useState(false),[relatedOnly,setRelatedOnly]=useState(false),[zoom,setZoom]=useState(1),[paths,setPaths]=useState([]),[help,setHelp]=useState(false);
  const [pinnedPassage,setPinnedPassage]=useState(null),[hoveredPassage,setHoveredPassage]=useState(null),[passageGroupFocused,setPassageGroupFocused]=useState(false),[readEvidence,setReadEvidence]=useState(null);
  const [inspectedEC,setInspectedEC]=useState(null),[candidatesOpen,setCandidatesOpen]=useState(false),[unsupportedOnly,setUnsupportedOnly]=useState(false),[filtersOpen,setFiltersOpen]=useState(false);
  const board=useRef(null),viewport=useRef(null),anchors=useRef({}),reader=useRef(null);
  const active=hovered||selected;
  const sourceFocus=hoveredPassage||(!hovered&&passageGroupFocused?pinnedPassage:null);
  const trace=sourceFocus?traceClaims(sourceFocus.ids):traceSelection(active,hovered&&hovered!==selected?null:setId);
  const pinnedTrace=passageGroupFocused&&pinnedPassage?traceClaims(pinnedPassage.ids):traceSelection(selected,setId);
  const visibilityTrace=hoveredPassage?trace:pinnedTrace;
  const visible=items=>relatedOnly&&visibilityTrace?items.filter(item=>visibilityTrace.nodeIds.has(item.id)):items;
  const filteredDCs=unsupportedOnly?dcs.filter(dc=>!dc.sets.length):dcs;
  const queue=pinnedPassage?.ids.length>1?pinnedPassage.ids.map(id=>byId[id]):filteredDCs;
  const visibleDCs=visible(hoveredPassage?dcs:filteredDCs),visibleECs=visible(ecs),visibleEvidence=visible(evidence);
  const clear=()=>{setSelected(null);setHovered(null);setHoveredPassage(null);setSetId(null);setExpandedSetIds([]);setPinnedPassage(null);setPassageGroupFocused(false);setInspectedEC(null);setCandidatesOpen(false)};
  const reset=()=>{clear();setSupportOnly(false);setRelatedOnly(false);setUnsupportedOnly(false);setFiltersOpen(false);setZoom(1);viewport.current?.scrollTo({left:0});board.current?.querySelectorAll('.column-body,.paper-copy').forEach(e=>e.scrollTop=0)};
  const reveal=id=>{
    const node=anchors.current[id],container=node?.closest('.node-scroll');
    if(node&&container){const a=node.getBoundingClientRect(),b=container.getBoundingClientRect();if(a.top<b.top||a.bottom>b.bottom)container.scrollTop+=(a.top-b.top)/(b.height/container.offsetHeight)-20;}
    if(!id?.startsWith('dc'))return;
    const passage=board.current?.querySelector(`[data-dc-ids~="${id}"]`),copy=passage?.closest('.paper-copy');
    if(passage&&copy){const a=passage.getBoundingClientRect(),b=copy.getBoundingClientRect();if(a.top<b.top||a.bottom>b.bottom)copy.scrollTop+=(a.top-b.top)/(b.height/copy.offsetHeight)-copy.clientHeight/3;}
  };
  const select=id=>{setSelected(id);setHovered(null);setSetId(null);setExpandedSetIds([]);setHoveredPassage(null);setPassageGroupFocused(false);if(!pinnedPassage?.ids.includes(id))setPinnedPassage(null);setInspectedEC(null);setCandidatesOpen(false);if(id?.startsWith('dc')&&byId[id].sets.length)setUnsupportedOnly(false);requestAnimationFrame(()=>reveal(id))};
  const inspect=id=>{
    setInspectedEC(id);setHovered(null);setHoveredPassage(null);setPassageGroupFocused(false);
    if(id){
      const sets=byId[selected]?.sets??[];
      const displayed=sets.find(set=>set.id===setId&&expandedSetIds.includes(set.id)&&set.members.includes(id))||sets.find(set=>expandedSetIds.includes(set.id)&&set.members.includes(id));
      setCandidatesOpen(!displayed);if(displayed)setSetId(displayed.id);
      requestAnimationFrame(()=>document.querySelector(`${displayed?`[data-set-id="${displayed.id}"] .set-evidence`:'.candidate-list'} [data-ec-id="${id}"]`)?.scrollIntoView({block:'nearest'}));
    }
  };
  const focusSet=value=>{setHovered(null);setHoveredPassage(null);setPassageGroupFocused(false);setSetId(value);setInspectedEC(null)};
  const changeSet=id=>{
    const closing=expandedSetIds.includes(id);
    setExpandedSetIds(current=>closing?current.filter(value=>value!==id):[...current,id]);
    if(!closing){focusSet(id);setCandidatesOpen(false)}else if(setId===id)focusSet(null);
  };
  const expandAllSets=expand=>{
    setExpandedSetIds(expand?byId[selected].sets.map(set=>set.id):[]);
    if(!expand){focusSet(null);setInspectedEC(null)}
  };
  const navigate=step=>{const index=queue.findIndex(dc=>dc.id===selected),next=queue[index+step];if(next)select(next.id)};
  const filterUnsupported=value=>{setPinnedPassage(null);setPassageGroupFocused(false);setHoveredPassage(null);setUnsupportedOnly(value);setHovered(null);if(value&&selected?.startsWith('dc')&&byId[selected].sets.length){const first=dcs.find(dc=>!dc.sets.length);if(first)select(first.id);else clear()}};
  useEffect(()=>{const key=e=>{if(e.key==='Escape'&&!reader.current?.open){if(filtersOpen){setFiltersOpen(false);document.querySelector('[aria-label="Filter graph"]')?.focus()}else if(help)setHelp(false);else clear()}};window.addEventListener('keydown',key);return()=>window.removeEventListener('keydown',key)},[filtersOpen,help]);
  useEffect(()=>{if(!filtersOpen)return;const outside=e=>{if(!e.target.closest('.filter-control'))setFiltersOpen(false)};document.addEventListener('pointerdown',outside);return()=>document.removeEventListener('pointerdown',outside)},[filtersOpen]);
  const measure=useCallback(()=>{
    if(!board.current)return;
    const rect=board.current.getBoundingClientRect(),scale=rect.width/board.current.offsetWidth;
    const sourcePositions=new Map(),paper=board.current.querySelector('.disclosure-paper').getBoundingClientRect(),copy=board.current.querySelector('.paper-copy').getBoundingClientRect();
    for(const span of board.current.querySelectorAll('[data-dc-ids]')){
      const r=span.getBoundingClientRect();if(r.bottom<=copy.top||r.top>=copy.bottom)continue;
      for(const id of span.dataset.dcIds.split(' '))if(!sourcePositions.has(`text-${id}`))sourcePositions.set(`text-${id}`,{...r.toJSON(),right:paper.right,top:Math.max(copy.top,r.top),height:Math.min(copy.bottom,r.bottom)-Math.max(copy.top,r.top)});
    }
    const nodePosition=id=>{
      if(id.startsWith('text-'))return sourcePositions.get(id);
      const node=anchors.current[id];if(!node)return null;const r=node.getBoundingClientRect(),parent=node.closest('.node-scroll');
      if(parent){const p=parent.getBoundingClientRect();if(r.top<p.top||r.bottom>p.bottom)return null;}
      return r;
    };
    setPaths(allEdges.map(edge=>{const a=nodePosition(edge.from),b=nodePosition(edge.to);if(!a||!b)return null;return {...edge,path:route({source:[(a.right-rect.left)/scale+3,(a.top+a.height/2-rect.top)/scale],target:[(b.left-rect.left)/scale-3,(b.top+b.height/2-rect.top)/scale]})}}).filter(Boolean));
  },[allEdges]);
  useLayoutEffect(()=>{measure();const observer=new ResizeObserver(measure);observer.observe(board.current);window.addEventListener('resize',measure);document.fonts.ready.then(measure);return()=>{observer.disconnect();window.removeEventListener('resize',measure)}},[measure]);
  useLayoutEffect(()=>{measure()},[zoom,relatedOnly,unsupportedOnly,selected,setId,hoveredPassage,pinnedPassage,passageGroupFocused,measure]);
  const bind=id=>({ref:el=>{anchors.current[id]=el},onMouseEnter:()=>{setHoveredPassage(null);setHovered(id)},onMouseLeave:()=>setHovered(null),onFocus:()=>{setHoveredPassage(null);setHovered(id)},onBlur:()=>setHovered(null),onClick:()=>{if(selected===id&&!(passageGroupFocused&&pinnedPassage?.ids.length>1))clear();else if(selected?.startsWith('dc')&&id.startsWith('ec')&&byId[selected].candidates.includes(id))inspect(id);else if(selected?.startsWith('dc')&&id.startsWith('ev')&&pinnedTrace?.nodeIds.has(id))openReader(id);else select(id)},'data-node-id':id,'aria-pressed':selected===id});
  const nodeClass=id=>`${trace&&!trace.nodeIds.has(id)?' is-muted':''}${(sourceFocus?sourceFocus.ids.includes(id):active===id)?' is-active':''}${inspectedEC===id?' is-inspected':''}${trace?.nodeIds.has(id)?' is-related':''}`;
  const openReader=id=>{setReadEvidence(id);reader.current.showModal()};
  const renderSegment=(segment,key)=>{
    const ids=segment.dcIds;if(!ids.length)return segment.text;
    const same=passage=>passage?.start===segment.start&&passage?.end===segment.end;
    const preview=()=>{setHovered(null);setHoveredPassage({ids,start:segment.start,end:segment.end})};
    const activate=()=>{
      if(!window.getSelection()?.isCollapsed)return;
      if(same(pinnedPassage)&&passageGroupFocused){clear();return;}
      const id=ids.includes(selected)?selected:ids[0];
      setPinnedPassage({ids,start:segment.start,end:segment.end});setPassageGroupFocused(true);
      setSelected(id);setHovered(null);setHoveredPassage(null);setSetId(null);setExpandedSetIds([]);setInspectedEC(null);setCandidatesOpen(false);setUnsupportedOnly(false);
      requestAnimationFrame(()=>reveal(id));
    };
    const highlighted=sourceFocus?same(sourceFocus):ids.includes(active);
    return <span key={key} role="button" tabIndex={0} data-dc-ids={ids.join(' ')} data-node-id={`text-${ids[0]}`} aria-pressed={same(pinnedPassage)||ids.includes(selected)}
      aria-label={`Trace passage to ${ids.map(id=>byId[id].label).join(', ')}: ${segment.text}`}
      className={`disclosure-span${highlighted?' is-active':ids.some(id=>trace?.nodeIds.has(id))?' is-related':''}${ids.length>1?' shared-passage':''}`}
      onMouseEnter={preview} onMouseLeave={()=>setHoveredPassage(null)} onFocus={preview} onBlur={()=>setHoveredPassage(null)} onClick={activate}
      onKeyDown={e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();activate()}}}>{segment.text}</span>;
  };
  return <div className={`app-shell${native?' native-case':''}`} data-case-kind={meta.kind}>
    <header className="app-header"><a className="brand" href="./" aria-label="BACE home"><Graph size={23} weight="bold"/><span>BACE</span><span className="brand-divider"/><span className="brand-subtitle">Evidence explorer</span></a><div className="case-meta">{picker}<span className="demo-badge">{native?'Saved assessment':'Illustrative data'}</span></div></header>
    <main>
      {loadNotice&&<div className={`load-notice${loadError?' load-error':''}`} role="status">{loadNotice}{loadError&&' The view below remains the last successfully loaded case.'}</div>}
      <div className="workspace-bar"><h1 className="sr-only">Disclosure &amp; evidence</h1><div className="toolbar">
        <div className="filter-control"><button className={`icon-button${relatedOnly||supportOnly?' active-control':''}`} onClick={()=>setFiltersOpen(!filtersOpen)} aria-label="Filter graph" title="Filter graph" aria-expanded={filtersOpen}><FadersHorizontal size={19}/>{(relatedOnly||supportOnly)&&<i className="filter-dot"/>}</button>
          {filtersOpen&&<div className="filter-popover" aria-label="Graph filters">
            <label className="toggle-label"><input type="checkbox" checked={relatedOnly} onChange={e=>setRelatedOnly(e.target.checked)} aria-label="Show related nodes only"/><span className="toggle-track"/><span>Related only</span></label>
            <label className="toggle-label"><input type="checkbox" checked={supportOnly} onChange={e=>setSupportOnly(e.target.checked)} aria-label="Show support memberships only"/><span className="toggle-track"/><span>Support only</span></label>
          </div>}
        </div>
        <button className="icon-button" onClick={reset} title="Reset view" aria-label="Reset view"><ArrowCounterClockwise size={18}/></button><button className="icon-button" onClick={()=>{setHelp(!help);setFiltersOpen(false)}} title="About this graph" aria-label="About this graph" aria-expanded={help}><Info size={19}/></button>
      </div></div>
      {help&&<aside className="help-panel"><div><strong>Read the connections in either direction.</strong><p>Normal lines are candidate relationships. Green lines belong to accepted support sets. Light outer lines trace extraction and source provenance. All ECs within a support set are required together (AND); different sets are alternatives (OR). A diagnosis belongs to an unsupported disclosure claim. Hover to preview a trace; click to pin it. Source passages highlight every mapped DC. Review their details in the bottom panel. Support is assessed within the supplied evidence.</p>{native&&<p>Case stages: complete. Overall run: {meta.runStatus}. Consumed artifact hashes were checked against saved receipts. These are saved automated assessments, not human validation. Display IDs are aliases; Source record shows the original identifiers.</p>}{native&&<div className="case-shortcuts"><button onClick={()=>{select(meta.examples.joint);setRelatedOnly(true);setHelp(false)}}>Joint support</button><button onClick={()=>{select(meta.examples.diagnosis);setRelatedOnly(true);setHelp(false)}}>Unsupported diagnosis</button></div>}</div><button className="icon-button" onClick={()=>setHelp(false)} aria-label="Close help"><X size={17}/></button></aside>}
      <section className="graph-frame" aria-label="Bidirectional evidence graph">
        <div className="graph-viewport" ref={viewport}><div className="zoom-wrapper" style={{width:zoom===1?'100%':`${zoom*100}%`}}><div className="graph-board" ref={board} style={{minWidth:1120,...(zoom!==1?{zoom}:{})}}>
          <svg className="edges" aria-hidden="true" data-testid="edges">{paths.map(edge=>{const connected=!trace||trace.edgeIds.has(edge.id),hidden=supportOnly&&edge.kind==='candidate';return <path key={edge.id} data-edge={edge.id} data-kind={edge.kind} data-highlighted={Boolean(trace&&connected)} d={edge.path} className={`edge edge-${edge.kind}${trace?connected?' edge-highlight':' edge-muted':''}${hidden?' edge-hidden':''}`}/>})}</svg>
          <section className="graph-column disclosure-column"><div className="column-header"><h2>Generated disclosure</h2><button className="icon-button expand-reader" onClick={()=>openReader(null)} aria-label="Expand generated disclosure" title="Expand for reading"><ArrowsOutSimple size={16}/></button></div><div className="column-body">
            <article className="disclosure-paper" aria-label="Complete generated disclosure"><div className="paper-copy" onScroll={measure}><Document text={disclosure.text} dcs={dcs} renderSegment={renderSegment}/></div>
            </article></div></section>
          <section className="graph-column dc-column"><div className="column-header"><h2>Disclosure claims</h2><button className={`icon-button unsupported-filter${unsupportedOnly?' active-control':''}`} title="Unsupported only" aria-label="Show unsupported claims only" aria-pressed={unsupportedOnly} onClick={()=>filterUnsupported(!unsupportedOnly)}><WarningCircle size={16}/></button><small>{(relatedOnly&&selected)||unsupportedOnly?`${visibleDCs.length}/`:''}{dcs.length}</small></div><div className={`column-body dc-list${native?' node-scroll':''}`} onScroll={measure}>{!visibleDCs.length&&<p className="empty-candidates">No claims in this view.</p>}{visibleDCs.map(dc=><button key={dc.id} {...bind(dc.id)} className={`claim-node dc-node${nodeClass(dc.id)}`} aria-label={`${dc.label}: ${dc.text}. ${outcome(dc)}`} title={dc.text}><span className="node-top"><strong>{dc.label}</strong>{dc.sets.length?<CheckCircle size={14} className="support-status" weight="fill"/>:<WarningCircle size={14} className="diagnosis-status" weight="fill"/>}</span><span className="node-short">{dc.short}</span>{dc.sourceStatus!=='Located'&&<span className="node-location">{dc.sourceStatus}</span>}</button>)}</div></section>
          <section className="graph-column ec-column"><div className="column-header"><h2>Evidence claims</h2><small>{relatedOnly&&selected?`${visibleECs.length}/`:''}{ecs.length}</small></div><div className={`column-body ec-list${native?' node-scroll':''}`} onScroll={measure}>{visibleECs.map(ec=><button key={ec.id} {...bind(ec.id)} className={`claim-node ec-node${nodeClass(ec.id)}`} aria-label={`${ec.label}: ${ec.text}`} title={ec.text}><span className="node-top"><strong>{ec.label}</strong></span><span className="node-short">{ec.short}</span>{ec.previewValue&&<span className="node-value">{ec.previewValue}</span>}</button>)}</div></section>
          <section className="graph-column evidence-column"><div className="column-header"><h2>Evidence list</h2><small>{relatedOnly&&selected?`${visibleEvidence.length}/`:''}{evidence.length}</small></div><div className={`column-body evidence-list${native?' node-scroll':''}`} onScroll={measure}>{visibleEvidence.map(ev=><button key={ev.id} {...bind(ev.id)} className={`evidence-card${nodeClass(ev.id)}`} aria-label={`${ev.label}: ${ev.title}`} title={ev.title}><div className="evidence-top"><span>{ev.label}</span><ArrowUpRight size={14}/></div><h3>{ev.title.replace(/\bgreenhouse gas\b/gi,'GHG')}</h3></button>)}</div></section>
        </div></div></div>
        <div className="graph-footer"><div className="legend"><span><i className="legend-line candidate-line"/>Candidate</span><span><i className="legend-line support-line"/>Support membership</span></div><div className="selection-hint">{selected?<button className="detail-jump" aria-label="View selection details" onClick={()=>document.querySelector('.detail-panel')?.scrollIntoView({block:'nearest'})}><PushPin size={12} weight="fill"/>{passageGroupFocused&&pinnedPassage?.ids.length>1?`${pinnedPassage.ids.length} DCs`:byId[selected].label}<ArrowDown size={12}/></button>:null}</div><div className="zoom-controls"><button className="icon-button" aria-label="Zoom out" disabled={zoom<=.8} onClick={()=>setZoom(z=>Math.max(.8,+(z-.1).toFixed(1)))}><MagnifyingGlassMinus size={16}/></button><span>{Math.round(zoom*100)}%</span><button className="icon-button" aria-label="Zoom in" disabled={zoom>=1.4} onClick={()=>setZoom(z=>Math.min(1.4,+(z+.1).toFixed(1)))}><MagnifyingGlassPlus size={16}/></button><button className="icon-button" aria-label="Fit graph" onClick={()=>{setZoom(1);viewport.current?.scrollTo({left:0})}}><ArrowsOutSimple size={16}/></button></div></div>
      </section>
      <Review model={model} id={selected} setId={setId} expandedSetIds={expandedSetIds} onSet={changeSet} onExpandAll={expandAllSets} onFocusSet={id=>focusSet(setId===id?null:id)} onSelect={select} onClose={clear} onReadEvidence={openReader} inspectedEC={inspectedEC} onInspect={inspect} candidatesOpen={candidatesOpen} onCandidates={setCandidatesOpen} queue={queue} onNavigate={navigate} passageIds={pinnedPassage?.ids??[]}/>
      <dialog ref={reader} className="document-reader" aria-labelledby="document-reader-title"><div className="reader-toolbar"><span>{readEvidence?byId[readEvidence].label:'Generated disclosure'}</span>{readEvidence&&<button className="icon-button reader-trace" title="Trace from this evidence" aria-label="Trace from this evidence" onClick={()=>{reader.current.close();select(readEvidence)}}><Graph size={18}/></button>}<button className="icon-button" aria-label="Close document reader" onClick={()=>reader.current.close()}><X size={21}/></button></div><article className="reader-document"><div className="reader-meta">{meta.company} · {readEvidence?byId[readEvidence].year:meta.year}<span>{meta.badge}</span></div><h2 id="document-reader-title" className={native&&!readEvidence?'sr-only':undefined}>{readEvidence?byId[readEvidence].title:disclosure.title}</h2><div className="reader-copy">{readEvidence?<p className="verbatim-evidence">{byId[readEvidence].text}</p>:<Document text={disclosure.text}/>}</div></article><div className="reader-footer"><span>{readEvidence?byId[readEvidence].sourceLabel||'Source evidence':'Complete generated disclosure'}</span><button onClick={()=>reader.current.close()}>Return to graph</button></div></dialog>
      <div className="sr-only" role="status" aria-live="polite">{selected?`${byId[selected].label} selected. ${selected.startsWith('dc')?outcome(byId[selected]):''}`:'No pinned selection'}</div>
    </main>
  </div>;
}
