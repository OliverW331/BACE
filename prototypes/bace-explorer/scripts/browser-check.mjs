import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {disclosure, dcs} from '../src/data.js';

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
 await fs.writeFile(`qa/${name}.png`,Buffer.from(image.data,'base64'));
};
await fs.mkdir('qa',{recursive:true});
await cdp('Runtime.enable');await cdp('Log.enable');await cdp('Page.enable');
await cdp('Emulation.setDeviceMetricsOverride',{width:1710,height:1000,deviceScaleFactor:1,mobile:false});
await cdp('Page.navigate',{url:'http://127.0.0.1:4173/?case=demo'});
for(let i=0;i<80;i++){if(await run('document.querySelectorAll("[data-edge]").length')===25)break;await sleep(100)}
await run('document.fonts.ready.then(()=>true)');await sleep(200);
const edgeCount=await run('document.querySelectorAll("[data-edge]").length');
assert.equal(edgeCount,25,'Fourteen source links and eleven candidate/support relationships render');
await capture('overview');
assert.deepEqual(await run(`Array.from(document.querySelectorAll('.paper-copy p')).map(p=>p.textContent)`),disclosure.paragraphs.map(p=>p.text),'Full original paragraphs must be preserved verbatim');
assert.equal(await run(`document.querySelectorAll('.paper-copy .passage-number,.paper-copy button').length`),0,'The source is not a numbered claim list');
assert.equal(await run(`document.querySelector('.paper-copy p').querySelectorAll('[data-dc-ids]').length`),3,'One source paragraph can contain multiple extracted claims');
assert.notEqual(await run(`document.querySelector('[data-node-id="text-dc1"]').textContent`),dcs[0].text,'Original source wording differs from canonical DC wording');
await click('[data-node-id="text-dc3"]');await moveAway();await sleep(150);
assert.equal(await run(`document.querySelector('[data-node-id="dc3"]').getAttribute('aria-pressed')`),'true','Clicking inline source text selects its DC');
await click('[aria-label="Expand generated disclosure"]');await sleep(100);
assert.equal(await run(`document.querySelector('.document-reader').open`),true);
assert.deepEqual(await run(`Array.from(document.querySelectorAll('.reader-copy p')).map(p=>p.textContent)`),disclosure.paragraphs.map(p=>p.text));
await capture('document-reader');
await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
await cdp('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await sleep(150);
assert.equal(await run(`document.querySelector('.document-reader').open`),false);
assert.equal(await run(`document.querySelector('[data-node-id="dc3"]').getAttribute('aria-pressed')`),'true','Closing the reader must preserve the pinned graph selection');
await click('[aria-label="Reset view"]');await moveAway();await sleep(100);

// A temporary hover must clear on exit without becoming a pinned selection.
const dc2Point=await run(`(()=>{const r=document.querySelector('[data-node-id="dc2"]').getBoundingClientRect();return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);
await cdp('Input.dispatchMouseEvent',{type:'mouseMoved',...dc2Point});await sleep(150);
assert.ok((await highlight()).includes('dc2-ec3'));
assert.equal(await run('document.querySelectorAll("[data-node-id][aria-pressed=true]").length'),0);
await moveAway();await sleep(100);
assert.equal((await highlight()).length,0);

await click('[data-node-id="dc1"]');await moveAway();await sleep(150);
assert.deepEqual(await highlight(),['dc1-ec1','dc1-ec2','dc1-ec6','ec1-ev1','ec2-ev1','ec6-ev1','text-dc1'].sort());
assert.ok((await run('document.querySelector("[data-testid=details]").innerText')).includes('AND'));
await capture('dc-support');
await cdp('Input.dispatchMouseEvent',{type:'mouseMoved',...dc2Point});await sleep(150);
assert.ok((await highlight()).includes('dc2-ec3'));
await moveAway();await sleep(150);
assert.ok((await highlight()).includes('dc1-ec1'),'Leaving hover restores the pinned DC');

await click('[data-testid="set-a"]');await moveAway();await sleep(100);
assert.deepEqual(await highlight(),['dc1-ec1','dc1-ec2','ec1-ev1','ec2-ev1','text-dc1'].sort());
await capture('support-set');
await click('[data-node-id="ev2"]');await moveAway();await sleep(100);
assert.deepEqual(await highlight(),['dc2-ec3','dc2-ec4','dc2-ec5','dc3-ec3','dc3-ec4','dc5-ec5','ec3-ev2','ec4-ev2','ec5-ev2','text-dc2','text-dc3','text-dc5'].sort());
await capture('evidence-reverse');
await click('[data-node-id="ec8"]');await moveAway();await sleep(100);
assert.deepEqual(await highlight(),['ec8-ev3']);
assert.ok((await run('document.querySelector("[data-testid=details]").innerText')).includes('Not selected as a candidate'));
await click('[data-node-id="dc2"]');await moveAway();await sleep(100);
assert.ok((await run('document.querySelector("[data-testid=details]").innerText')).includes('Factual boundary distortion'));
assert.equal(await run('document.querySelectorAll(".edge-support.edge-highlight").length'),0);
await capture('diagnosis');
await click('[data-node-id="dc4"]');await moveAway();await sleep(100);
assert.deepEqual(await highlight(),['text-dc4']);
assert.ok((await run(`document.querySelector('.empty-candidates').textContent`)).includes('No candidates selected'));
await click('[aria-label="Show support memberships only"]');
assert.equal(await run('document.querySelectorAll(".edge-candidate:not(.edge-hidden)").length'),0);
await click('[aria-label="Reset view"]');await moveAway();await sleep(100);
assert.equal((await highlight()).length,0);
await click('[data-node-id="dc3"]');await moveAway();
await cdp('Input.dispatchKeyEvent',{type:'keyDown',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});
await cdp('Input.dispatchKeyEvent',{type:'keyUp',key:'Escape',code:'Escape',windowsVirtualKeyCode:27});await sleep(100);
assert.equal((await highlight()).length,0);
await click('[aria-label="Zoom in"]');await moveAway();await sleep(100);
assert.ok((await run('document.querySelector(".zoom-controls").innerText')).includes('110%'));
await click('[aria-label="Fit graph"]');await moveAway();
await cdp('Emulation.setDeviceMetricsOverride',{width:1440,height:900,deviceScaleFactor:1,mobile:false});await sleep(200);
await run('window.scrollTo(0,0)');await capture('desktop-1440');
const desktopOverflow=await run('document.documentElement.scrollWidth>innerWidth');
await cdp('Emulation.setDeviceMetricsOverride',{width:430,height:900,deviceScaleFactor:1,mobile:false});await sleep(200);
await run('window.scrollTo(0,0)');await capture('narrow');
const narrowOverflow=await run('document.documentElement.scrollWidth>innerWidth');
await click('[data-node-id="dc6"]');await moveAway();await sleep(150);
assert.ok(await run(`(()=>{const passage=document.querySelector('[data-node-id="text-dc6"]').getBoundingClientRect(),copy=document.querySelector('.paper-copy').getBoundingClientRect();return passage.bottom<=copy.bottom+1&&passage.top>=copy.top-1})()`),'Selecting a DC reveals its source passage in the scrollable reader');
await click('[aria-label="Expand generated disclosure"]');await sleep(100);
assert.equal(await run(`document.querySelector('.document-reader').scrollWidth>document.querySelector('.document-reader').clientWidth`),false,'Expanded document has no horizontal overflow at narrow width');
await capture('document-reader-narrow');
await click('[aria-label="Close document reader"]');
assert.equal(await run(`document.querySelector('[data-node-id="dc6"]').getAttribute('aria-pressed')`),'true');
await click('[aria-label="Reset view"]');await moveAway();await sleep(100);

assert.equal(desktopOverflow,false);
assert.equal(narrowOverflow,false,'Only the graph viewport may scroll horizontally');
await cdp('Emulation.setDeviceMetricsOverride',{width:1710,height:803,deviceScaleFactor:1,mobile:false});await sleep(200);
await run('window.scrollTo(0,0)');await capture('reference-viewport');
const geometry=await run(`Array.from(document.querySelectorAll('.graph-column,.disclosure-paper,.graph-board')).map(e=>({class:e.className,rect:e.getBoundingClientRect().toJSON()}))`);
const clippedNodes=await run(`(()=>{const b=document.querySelector('.graph-board').getBoundingClientRect();return Array.from(document.querySelectorAll('[data-node-id]')).filter(e=>e.getBoundingClientRect().bottom>b.bottom).map(e=>e.dataset.nodeId)})()`);
assert.deepEqual(clippedNodes,[],'No graph node may be clipped by the graph footer');
await click('[data-node-id="dc2"]');await moveAway();await sleep(150);
await click('[aria-label="View selection details"]');await moveAway();await sleep(150);
assert.ok(await run(`(()=>{const r=document.querySelector('.review-heading').getBoundingClientRect();return r.bottom<=innerHeight+1&&r.top>=0})()`),'View details reveals the inspector at a shorter viewport');
assert.deepEqual(errors,[],'No browser runtime errors');
const report={passed:true,edgeCount,desktopOverflow,narrowOverflow,errors,geometry,checks:['Verbatim original source and paragraph structure','Inline passage-to-DC selection','Expanded reading and selection preservation','Narrow reader and source passage scrolling','Transient hover and pinned-state restoration','View details at a shorter viewport','DC-to-EC highlighting','Source-to-DC reverse highlighting','Exact support-set focus','Unused EC remains reachable','Diagnosis shown at DC level','Empty-candidate DC is reachable','Support-only filter','Reset','Escape','Zoom and fit']};
await fs.writeFile('qa/browser-check.json',JSON.stringify(report,null,2));
console.log(JSON.stringify(report,null,2));ws.close();
