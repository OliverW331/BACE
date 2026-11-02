import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {openBrowser} from './cdp-browser.mjs';
import {CASE_ID} from '../server/native-case.mjs';

const b=await openBrowser();
const {run,click,key,waitFor,moveAway,sleep,cdp,capture,viewport}=b;
const data=await (await fetch(`http://127.0.0.1:4173/api/bace/cases/${CASE_ID}`)).json();
const byId=Object.fromEntries([...data.dcs,...data.ecs,...data.evidence].map(item=>[item.id,item]));
const activeDCs=()=>run(`Array.from(document.querySelectorAll('.dc-node.is-active')).map(e=>e.dataset.nodeId).sort()`);
const anchor=()=>run(`document.querySelector('[data-review-anchor]')?.dataset.reviewAnchor`);
const settle=async()=>{await moveAway();await sleep(120)};
const hover=async selector=>{
  const p=await run(`(()=>{const e=document.querySelector(${JSON.stringify(selector)});e.scrollIntoView({block:'nearest'});const r=e.getClientRects()[0];return{x:r.x+r.width/2,y:r.y+r.height/2}})()`);
  await cdp('Input.dispatchMouseEvent',{type:'mouseMoved',...p});await sleep(350);
};
const hoverShot=async name=>{const shot=await cdp('Page.captureScreenshot',{format:'png',captureBeyondViewport:false});await fs.writeFile(`qa/native-passage-${name}.png`,Buffer.from(shot.data,'base64'))};
try {
  await waitFor('document.querySelector("[data-case-kind=native]")');await run('document.fonts.ready.then(()=>true)');await settle();
  const shared='.shared-passage',single='.disclosure-span:not(.shared-passage)';
  const ids=await run(`document.querySelector('${shared}').dataset.dcIds.split(' ')`);
  const singleIds=await run(`document.querySelector('${single}').dataset.dcIds.split(' ')`);
  await hover(single);assert.deepEqual(await activeDCs(),singleIds);
  const singleColor=await run(`getComputedStyle(document.querySelector('${single}')).backgroundColor`);
  assert.equal(await anchor(),undefined);await hoverShot('single-hover');
  await hover(shared);assert.deepEqual(await activeDCs(),[...ids].sort());
  assert.equal(await run(`getComputedStyle(document.querySelector('${shared}')).backgroundColor`),singleColor);
  assert.equal(await run(`getComputedStyle(document.querySelector('${shared}')).textDecorationLine`),'none');
  assert.equal(await run(`document.querySelectorAll('.disclosure-span[title]').length`),0);
  assert.equal(await anchor(),undefined);await hoverShot('shared-hover');
  await settle();assert.deepEqual(await activeDCs(),[]);

  const boardBefore=await run(`document.querySelector('.graph-frame').getBoundingClientRect().top+scrollY`);
  await click(shared);await settle();
  assert.deepEqual(await activeDCs(),[...ids].sort());
  assert.equal(await run(`document.querySelectorAll('.passage-choices').length`),0);
  assert.equal(await run(`document.querySelector('.graph-frame').getBoundingClientRect().top+scrollY`),boardBefore,'No extra panel shifts the graph');
  assert.equal(await run(`document.querySelectorAll('.detail-panel .passage-switcher button').length`),ids.length);
  assert.equal(await run(`document.querySelectorAll('.detail-panel').length`),1);
  await capture('qa/native-passage-pinned.png');
  await hover(single);assert.deepEqual(await activeDCs(),singleIds);await settle();
  assert.deepEqual(await activeDCs(),[...ids].sort(),'Leaving another passage restores the entire pinned group');

  await click(`[aria-label="Review ${byId[ids[1]].label}"]`);await settle();
  assert.equal(await anchor(),ids[1]);assert.deepEqual(await activeDCs(),[ids[1]]);
  assert.equal(await run(`document.querySelector('.detail-primary h2').textContent`),byId[ids[1]].text);
  await click('[aria-label="Next disclosure claim"]');await settle();assert.equal(await anchor(),ids[2]);
  await click('[aria-label="Previous disclosure claim"]');await settle();assert.equal(await anchor(),ids[1]);
  await click('[aria-label="View selection details"]');await capture('qa/native-passage-review.png');
  const support=byId[ids[1]].sets[0];
  await click(`[data-testid="set-${support.id}"]`);await settle();
  assert.deepEqual(await run(`Array.from(document.querySelectorAll('.set-evidence .ec-full-text')).map(e=>e.textContent)`),support.members.map(id=>byId[id].text));
  await hover(shared);assert.deepEqual(await activeDCs(),[...ids].sort());await settle();
  assert.equal(await anchor(),ids[1]);
  assert.equal(await run(`document.querySelector('[data-testid="set-${support.id}"]').getAttribute('aria-expanded')`),'true');
  await click('.set-evidence .ec-sources>button');await key('Escape');await settle();
  assert.equal(await anchor(),ids[1]);
  assert.equal(await run(`document.querySelectorAll('.passage-switcher button').length`),ids.length);

  await click('[aria-label="Filter graph"]');await click('[aria-label="Show related nodes only"]');await click('[aria-label="Filter graph"]');await settle();
  await hover(shared);assert.deepEqual(await activeDCs(),[...ids].sort(),'All mapped DCs appear even during a filtered preview');await settle();
  assert.deepEqual(await run(`Array.from(document.querySelectorAll('.dc-node')).map(e=>e.dataset.nodeId)`),[ids[1]]);
  await click('[aria-label="Reset view"]');await settle();
  await run(`document.querySelector('${shared}').focus()`);await sleep(100);assert.deepEqual(await activeDCs(),[...ids].sort());
  await key('Enter');await settle();assert.deepEqual(await activeDCs(),[...ids].sort());
  await click(`[aria-label="Review ${byId[ids[1]].label}"]`);await settle();
  await viewport(430,900);await click('[aria-label="View selection details"]');await capture('qa/native-passage-narrow.png');
  assert.equal(await run('document.documentElement.scrollWidth>innerWidth'),false);
  for(const id of ids){await click(`[aria-label="Review ${byId[id].label}"]`);await settle();assert.equal(await anchor(),id)}
  assert.deepEqual(b.errors,[]);
  const report={passed:true,checks:['Unified single/shared source hover and color','Every mapped DC highlighted','No source tooltip or top chooser','Pinned group restoration','One bottom review with mapped-DC switches','Per-DC text and exact support sets','Group navigation and reader return','Filtered hover restores pinned view','Keyboard activation','Narrow layout and switches'],errors:b.errors,viewports:[[1710,803],[430,900]]};
  await fs.writeFile('qa/native-passage-check.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
} finally {b.close()}
