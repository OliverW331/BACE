import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {openBrowser} from './cdp-browser.mjs';
import {CASE_ID} from '../server/native-case.mjs';

const b=await openBrowser(),{run,click,key,waitFor,moveAway,sleep,capture,viewport}=b;
const data=await (await fetch(`http://127.0.0.1:4173/api/bace/cases/${CASE_ID}`)).json();
const dc=data.dcs.find(dc=>dc.id===data.meta.examples.inferred),[first,second,third]=dc.sets;
const byId=Object.fromEntries([...data.dcs,...data.ecs,...data.evidence].map(item=>[item.id,item]));
const settle=async()=>{await moveAway();await sleep(150)};
const openIds=()=>run(`Array.from(document.querySelectorAll('.set-button[aria-expanded="true"]')).map(e=>e.closest('[data-set-id]').dataset.setId)`);
const focusId=()=>run(`document.querySelector('.set-focus[aria-pressed="true"]')?.closest('[data-set-id]').dataset.setId`);
try{
  await waitFor('document.querySelector("[data-case-kind=native]")');await run('document.fonts.ready.then(()=>true)');
  await click(`[data-node-id="${dc.id}"]`);await settle();
  await click('[aria-label="Filter graph"]');await click('[aria-label="Show related nodes only"]');await click('[aria-label="Filter graph"]');
  await click(`[data-testid="set-${first.id}"]`);await click(`[data-testid="set-${second.id}"]`);await settle();
  assert.deepEqual(await openIds(),[first.id,second.id],'Opening the second set preserves the first');
  assert.equal(await focusId(),second.id);
  assert.deepEqual(await run(`Array.from(document.querySelectorAll('.ec-node')).map(e=>e.dataset.nodeId).sort()`),[...second.members].sort());
  await click(`[data-testid="set-${first.id}"]`);await settle();
  assert.deepEqual(await openIds(),[second.id]);assert.equal(await focusId(),second.id,'Closing another set preserves graph focus');
  await click('[aria-label="Expand all support sets"]');await settle();
  assert.deepEqual(await openIds(),dc.sets.map(set=>set.id));assert.equal(await focusId(),second.id,'Bulk expansion preserves graph focus');
  for(const set of dc.sets){
    assert.deepEqual(await run(`Array.from(document.querySelectorAll('[data-set-id="${set.id}"] .ec-full-text')).map(e=>e.textContent)`),set.members.map(id=>byId[id].text));
    assert.equal(await run(`document.querySelectorAll('[data-set-id="${set.id}"] .set-conjunction').length`),set.members.length-1);
  }
  assert.equal(await run(`document.querySelectorAll('.set-alternative').length`),dc.sets.length-1);
  await click('[aria-label="View selection details"]');await run(`document.querySelector('.detail-secondary').scrollTop=0`);await capture('qa/native-multiset-all-open.png');
  await click('[aria-label="Focus set 1 in graph"]');await settle();
  assert.deepEqual(await openIds(),dc.sets.map(set=>set.id));assert.equal(await focusId(),first.id);
  assert.deepEqual(await run(`Array.from(document.querySelectorAll('.ec-node')).map(e=>e.dataset.nodeId).sort()`),[...first.members].sort(),'Focus uses one exact group, not the union of open alternatives');
  await click(`[data-set-id="${first.id}"] .ec-sources>button`);await key('Escape');await settle();
  assert.deepEqual(await openIds(),dc.sets.map(set=>set.id));assert.equal(await focusId(),first.id);
  assert.equal(await run(`document.querySelector('[data-review-anchor]').dataset.reviewAnchor`),dc.id);
  await click(`[data-testid="set-${third.id}"]`);await settle();
  assert.deepEqual(await openIds(),dc.sets.filter(set=>set.id!==third.id).map(set=>set.id));
  await click('[aria-label="Expand all support sets"]');await settle();
  await click('[aria-label="Collapse all support sets"]');await settle();
  assert.deepEqual(await openIds(),[]);assert.equal(await focusId(),undefined);
  await run(`document.querySelector('[aria-label="Expand all support sets"]').focus()`);await key('Enter');await settle();
  assert.deepEqual(await openIds(),dc.sets.map(set=>set.id));
  await viewport(430,900);await click('[aria-label="View selection details"]');await capture('qa/native-multiset-narrow.png');
  assert.equal(await run('document.documentElement.scrollWidth>innerWidth'),false);
  await click('[aria-label="Collapse all support sets"]');await settle();assert.deepEqual(await openIds(),[]);
  await click('[aria-label="Expand all support sets"]');await settle();
  await click('[aria-label="Next disclosure claim"]');await settle();assert.deepEqual(await openIds(),[],'Switching DCs clears stale expansion IDs');
  assert.equal(await focusId(),undefined);
  assert.deepEqual(b.errors,[]);
  const report={passed:true,checks:['Independent set expansion/collapse','Expand all and collapse all','Bulk expansion preserves exact graph focus','OR alternatives and AND members remain separate','Explicit refocus without collapsing content','Full EC text fidelity','Reader return preserves all expansions and DC','Keyboard bulk expansion','Narrow layout','No stale expansion state across DCs'],errors:b.errors,viewports:[[1710,803],[430,900]]};
  await fs.writeFile('qa/native-multiset-check.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
}finally{b.close()}
