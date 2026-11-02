import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {CASE_ID} from '../server/native-case.mjs';
import {createGraphModel} from '../src/graph-model.js';

const base='http://127.0.0.1:9334';
const tab=await (await fetch(`${base}/json/new?http://127.0.0.1:4173`,{method:'PUT'})).json();
const ws=new WebSocket(tab.webSocketDebuggerUrl);
await new Promise((resolve,reject)=>{ws.addEventListener('open',resolve,{once:true});ws.addEventListener('error',reject,{once:true})});
let seq=0;const pending=new Map(),errors=[];
ws.addEventListener('message',event=>{
 const msg=JSON.parse(event.data);
 if(msg.id){const item=pending.get(msg.id);if(item){pending.delete(msg.id);msg.error?item.reject(msg.error):item.resolve(msg.result)}}
 if(msg.method==='Runtime.exceptionThrown')errors.push(msg.params.exceptionDetails);
 if(msg.method==='Log.entryAdded'&&msg.params.entry.level==='error')errors.push(msg.params.entry);
});
const cdp=(method,params={})=>new Promise((resolve,reject)=>{
 const id=++seq;pending.set(id,{resolve,reject});ws.send(JSON.stringify({id,method,params}));
});
const run=async expression=>{
 const r=await cdp('Runtime.evaluate',{expression,returnByValue:true,awaitPromise:true});
 if(r.exceptionDetails)throw Error(JSON.stringify(r.exceptionDetails));
 return r.result.value;
};
const sleep=ms=>new Promise(resolve=>setTimeout(resolve,ms));
const click=async selector=>{
 if((selector.includes('Show related nodes only')||selector.includes('Show support memberships only'))&&!await run(`document.querySelector(${JSON.stringify(selector)})!==null`))await click('[aria-label="Filter graph"]');
 const p=await run(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});if(!e)throw Error('Missing target');e.scrollIntoView({block:'nearest',inline:'nearest'});const r=e.getClientRects()[0];return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);
 await cdp('Input.dispatchMouseEvent',{type:'mouseMoved',...p});
 await cdp('Input.dispatchMouseEvent',{type:'mousePressed',button:'left',clickCount:1,...p});
 await cdp('Input.dispatchMouseEvent',{type:'mouseReleased',button:'left',clickCount:1,...p});
 await sleep(100);
};
const moveAway=()=>cdp('Input.dispatchMouseEvent',{type:'mouseMoved',x:800,y:95});
const highlight=()=>run(`Array.from(document.querySelectorAll('[data-edge][data-highlighted="true"]')).map(e=>e.dataset.edge).sort()`);
const capture=async name=>{
 await moveAway();await sleep(180);
 const image=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});
 await fs.writeFile(`qa/native-${name}.png`,Buffer.from(image.data,'base64'));
};

const payload=await (await fetch(`http://127.0.0.1:4173/api/bace/cases/${CASE_ID}`)).json();
assert.ok(payload.meta,'Native endpoint must return a case');
const model=createGraphModel(payload), examples=payload.meta.examples;
await fs.mkdir('qa',{recursive:true});
await cdp('Runtime.enable');await cdp('Log.enable');await cdp('Page.enable');
await cdp('Emulation.setDeviceMetricsOverride',{width:1710,height:1000,deviceScaleFactor:1,mobile:false});
await cdp('Page.navigate',{url:'http://127.0.0.1:4173/'});
for(let i=0;i<100;i++){if(await run(`document.querySelector('[data-case-kind="native"]')!==null`))break;await sleep(100)}
assert.equal(await run(`document.querySelector('[data-case-kind="native"]')!==null`),true);
await run('document.fonts.ready.then(()=>true)');await sleep(300);
assert.equal(await run(`document.querySelectorAll('.dc-node').length`),payload.dcs.length);
assert.equal(await run(`document.querySelectorAll('.ec-node').length`),payload.ecs.length);
assert.equal(await run(`document.querySelectorAll('.evidence-card').length`),payload.evidence.length);
assert.equal(await run(`document.querySelectorAll('.paper-copy table tbody tr').length`),7,'Generated table is rendered as a real table');
await capture('overview');
// Pin the real case's jointly sufficient support set.
await click('[aria-label="About this graph"]');await click('.case-shortcuts button:first-of-type');await moveAway();await sleep(200);
assert.equal(await run(`document.querySelector('.dc-node').dataset.nodeId`),examples.joint);
assert.deepEqual(await highlight(),[...model.traceSelection(examples.joint).edgeIds].sort());
await click('[data-testid="set-1"]');await moveAway();await sleep(200);
assert.deepEqual(await highlight(),[...model.traceSelection(examples.joint,'1').edgeIds].sort());
assert.equal(await run(`document.querySelectorAll('.ec-node').length`),2,'Only the joint members remain in focused set view');
await capture('joint-support');
// Alternative inferred groups remain separate, even when they share a target DC.
await click('[aria-label="Reset view"]');await moveAway();await sleep(100);
await click(`[data-node-id="${examples.inferred}"]`);await moveAway();await sleep(100);
await click('[aria-label="Show related nodes only"]');await moveAway();await sleep(100);
assert.equal(await run(`document.querySelectorAll('.set-button').length`),model.byId[examples.inferred].sets.length);
await click('[data-testid="set-2"]');await moveAway();await sleep(150);
assert.deepEqual(await highlight(),[...model.traceSelection(examples.inferred,'2').edgeIds].sort());
await capture('alternative-support');

// Saved diagnosis is displayed verbatim, even when it is an inconvenient result.
await click('[aria-label="Reset view"]');await moveAway();await sleep(150);
await click('[aria-label="About this graph"]');await click('.case-shortcuts button:last-of-type');await moveAway();await sleep(200);
assert.equal(await run(`document.querySelector('.diagnosis-rationale').textContent`),model.byId[examples.diagnosis].rationale);
assert.equal(await run(`document.querySelector('.diagnosis-title h3').textContent`),model.byId[examples.diagnosis].diagnosis);
assert.equal(await run(`document.querySelectorAll('.edge-support.edge-highlight').length`),0);
assert.ok((await highlight()).every(id=>model.traceSelection(examples.diagnosis).edgeIds.has(id)));
await click('[aria-label="View selection details"]');await capture('diagnosis');
// Reverse traversal from original evidence, including all related DCs in the list.
await click('[aria-label="Reset view"]');await moveAway();await sleep(150);
await click('[data-node-id="ev3"]');await moveAway();await sleep(100);
await click('[aria-label="Show related nodes only"]');await moveAway();await sleep(150);
const expectedDCs=payload.dcs.filter(d=>model.traceSelection('ev3').nodeIds.has(d.id)).map(d=>d.id).sort();
assert.deepEqual(await run(`Array.from(document.querySelectorAll('.dc-node')).map(e=>e.dataset.nodeId).sort()`),expectedDCs);
assert.ok((await highlight()).every(id=>model.traceSelection('ev3').edgeIds.has(id)));
await capture('reverse');
await click('.read-evidence');await moveAway();await sleep(100);
assert.equal(await run(`document.querySelector('.verbatim-evidence').textContent`),model.byId.ev3.text);
await capture('evidence-reader');await click('[aria-label="Close document reader"]');
// Shared source spans highlight every mapped DC; details stay in the bottom review.
await click('[aria-label="Reset view"]');await moveAway();await sleep(150);
const sharedIds=await run(`document.querySelector('.shared-passage').dataset.dcIds.split(' ')`);
await click('.shared-passage');await moveAway();await sleep(100);
assert.equal(await run(`document.querySelectorAll('.detail-panel .passage-switcher button').length`),sharedIds.length);
await capture('shared-passage');await click('.passage-switcher button');await moveAway();await sleep(150);
assert.equal(await run(`document.querySelector('[data-node-id="${sharedIds[0]}"]').getAttribute('aria-pressed')`),'true');
await click('[aria-label="Expand generated disclosure"]');await moveAway();await sleep(150);
assert.equal(await run(`document.querySelectorAll('.reader-copy table tbody tr').length`),7);
const tail=payload.disclosure.text.split('\n\n').at(-1);
assert.ok((await run(`document.querySelector('.reader-copy').textContent`)).includes(tail));
await capture('disclosure-reader');await click('[aria-label="Close document reader"]');
await click('[aria-label="Reset view"]');await moveAway();await sleep(150);
await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});await sleep(200);await run('window.scrollTo(0,0)');await capture('desktop-1440');
assert.equal(await run('document.documentElement.scrollWidth>innerWidth'),false);
await cdp('Emulation.setDeviceMetricsOverride',{width:430,height:900,deviceScaleFactor:1,mobile:false});await sleep(200);await run('window.scrollTo(0,0)');await capture('narrow');
assert.equal(await run('document.documentElement.scrollWidth>innerWidth'),false);
await click('[aria-label="Expand generated disclosure"]');await moveAway();await sleep(150);await capture('reader-narrow');
assert.equal(await run(`document.querySelector('.document-reader').scrollWidth>document.querySelector('.document-reader').clientWidth`),false);
await click('[aria-label="Close document reader"]');
await cdp('Emulation.setDeviceMetricsOverride',{width:1710,height:803,deviceScaleFactor:1,mobile:false});await sleep(200);await run('window.scrollTo(0,0)');await capture('reference-viewport');
assert.deepEqual(errors,[]);
const report={passed:true,caseId:CASE_ID,counts:payload.meta.counts,examples,errors,checks:['Original generated disclosure and table','All DCs, ECs and supplied evidence available','Joint support-set focus','Alternative inferred support-set isolation','Saved diagnosis and rationale','Reverse traversal','Original evidence reader','Shared-passage group and bottom review','Full disclosure reader','Desktop and narrow layout'],viewports:[[1710,1000],[1710,803],[1440,900],[430,900]]};
await fs.writeFile('qa/native-browser-check.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));ws.close();
