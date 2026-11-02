import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {openBrowser} from './cdp-browser.mjs';
import {CASE_ID} from '../server/native-case.mjs';
import {createGraphModel} from '../src/graph-model.js';

const browser=await openBrowser();
const {run,click,key,waitFor,viewport,capture,moveAway,sleep,cdp,errors}=browser;
const payload=await (await fetch(`http://127.0.0.1:4173/api/bace/cases/${CASE_ID}`)).json();
const model=createGraphModel(payload),{joint,diagnosis,inferred}=payload.meta.examples;
const anchor=()=>run(`document.querySelector('[data-review-anchor]')?.dataset.reviewAnchor`);
const settle=async()=>{await moveAway();await sleep(120)};
const reset=async()=>{await click('[aria-label="Reset view"]');await settle()};
const filter=async label=>{await click('[aria-label="Filter graph"]');await click(`[aria-label="${label}"]`);await click('[aria-label="Filter graph"]');await settle()};
const checks=[];
try {
  await waitFor(`document.querySelector('[data-case-kind="native"]')`);await run('document.fonts.ready.then(()=>true)');await settle();
  assert.equal(await run(`document.querySelector('[data-review-anchor]')`),null);
  assert.equal(await run(`document.querySelectorAll('.paper-header,.paper-footer,.evidence-meta,.empty-detail,.page-footer,.column-header>span').length`),0);
  await capture('qa/native-refined-overview.png');
  checks.push('Default view omits redundant secondary labels and empty instruction panel');

  // Temporary graph focus cannot mount a detail panel or move the page.
  await run(`document.querySelector('[data-node-id="${joint}"]').focus()`);await sleep(100);
  assert.equal(await anchor(),undefined);
  await key('Enter');await settle();assert.equal(await anchor(),joint);
  await filter('Show related nodes only');
  const set=model.byId[joint].sets[0];
  await click(`[data-testid="set-${set.id}"]`);await settle();
  assert.deepEqual(await run(`Array.from(document.querySelectorAll('.set-evidence .ec-full-text')).map(e=>e.textContent)`),set.members.map(id=>model.byId[id].text));
  assert.equal(await run(`document.querySelectorAll('.set-conjunction').length`),set.members.length-1);
  await click('[aria-label="View selection details"]');await capture('qa/native-refined-support.png');
  const scrollBefore=await run(`({page:scrollY,detail:document.querySelector('.detail-secondary').scrollTop})`);
  const member=set.members[0],source=model.byId[member].sources[0];
  const sourceButton=`[aria-label="Read ${model.byId[source].label} for ${model.byId[member].label}"]`;
  await click(sourceButton);await settle();
  assert.equal(await run(`document.querySelector('.verbatim-evidence').textContent`),model.byId[source].text);
  await key('Escape');await settle();
  assert.equal(await anchor(),joint);
  assert.equal(await run(`document.querySelector('[data-testid="set-${set.id}"]').getAttribute('aria-expanded')`),'true');
  assert.deepEqual(await run(`({page:scrollY,detail:document.querySelector('.detail-secondary').scrollTop})`),scrollBefore);
  assert.equal(await run(`document.activeElement.getAttribute('aria-label')`),`Read ${model.byId[source].label} for ${model.byId[member].label}`);
  checks.push('Keyboard pinning; full joint EC texts; AND membership; source fidelity; reader restores DC, set, scroll, and focus');

  await click(`[data-node-id="${member}"]`);await settle();
  assert.equal(await anchor(),joint,'Graph EC inspection preserves the pinned DC');
  assert.equal(await run(`document.querySelector('.set-evidence [data-ec-id="${member}"] .ec-full-text').textContent`),model.byId[member].text);
  assert.equal(await run(`document.querySelector('.candidate-list')`),null,'An already visible set member is not duplicated in an expanded candidate list');
  assert.equal(await run(`document.querySelector('[data-testid="set-${set.id}"]').getAttribute('aria-expanded')`),'true');
  await click(`.set-evidence [aria-label="Trace from ${model.byId[member].label}"]`);await settle();
  assert.equal(await anchor(),member,'An explicit trace action changes the review anchor');
  checks.push('Inspecting graph EC preserves DC; explicit reverse trace changes anchor');

  await reset();await click(`[data-node-id="${inferred}"]`);await settle();await filter('Show related nodes only');
  for(const alternative of model.byId[inferred].sets){
    await click(`[data-testid="set-${alternative.id}"]`);await settle();
    assert.equal(await anchor(),inferred);
    assert.deepEqual(await run(`Array.from(document.querySelectorAll('[data-set-id="${alternative.id}"] .set-evidence [data-ec-id]')).map(e=>e.dataset.ecId)`),alternative.members);
    assert.deepEqual(await run(`Array.from(document.querySelectorAll('.ec-node')).map(e=>e.dataset.nodeId).sort()`),[...alternative.members].sort());
  }
  await click('[aria-label="View selection details"]');await capture('qa/native-refined-alternatives.png');
  checks.push('Every alternative retains exact isolated membership and pinned DC');

  await reset();await click(`[data-node-id="${diagnosis}"]`);await settle();
  assert.equal(await run(`document.querySelector('.diagnosis-rationale').textContent`),model.byId[diagnosis].rationale);
  const candidate=model.byId[diagnosis].candidates[0];
  await click(`.candidate-list [data-ec-id="${candidate}"] .ec-summary`);await settle();
  assert.equal(await anchor(),diagnosis);
  assert.equal(await run(`document.querySelector('.candidate-list .ec-full-text').textContent`),model.byId[candidate].text);
  await click('[aria-label="View selection details"]');await capture('qa/native-refined-diagnosis.png');
  await click('.candidate-list .ec-sources>button');await settle();
  await click('[aria-label="Close document reader"]');await settle();assert.equal(await anchor(),diagnosis);
  assert.equal(await run(`document.querySelector('.ec-summary[aria-expanded="true"]').closest('article').dataset.ecId`),candidate);
  checks.push('Diagnosis and candidate/source comparison preserve verbatim rationale and active DC');

  await reset();await click('[data-node-id="dc1"]');await settle();
  await click('[aria-label="Show unsupported claims only"]');await settle();
  const unsupported=payload.dcs.filter(dc=>!dc.sets.length);
  assert.equal(await anchor(),unsupported[0].id);
  assert.deepEqual(await run(`Array.from(document.querySelectorAll('.dc-node')).map(e=>e.dataset.nodeId)`),unsupported.map(dc=>dc.id));
  assert.equal(await run(`document.querySelector('[aria-label="Previous disclosure claim"]').disabled`),true);
  await click('[aria-label="Next disclosure claim"]');await settle();assert.equal(await anchor(),unsupported[1].id);
  await click('[aria-label="Previous disclosure claim"]');await settle();assert.equal(await anchor(),unsupported[0].id);
  await filter('Show support memberships only');
  assert.equal(await run(`document.querySelectorAll('.edge-candidate:not(.edge-hidden)').length`),0);
  await click('[aria-label="Filter graph"]');await key('Escape');await settle();
  assert.equal(await anchor(),unsupported[0].id,'Escape closes the filter before clearing the review');
  assert.equal(await run(`document.activeElement.getAttribute('aria-label')`),'Filter graph');
  checks.push('Unsupported queue, navigation boundaries, support filter, and menu Escape');

  for(const [width,height] of [[1440,900],[430,900]]){
    await viewport(width,height);await run('window.scrollTo(0,0)');await capture(`qa/native-refined-${width}.png`);
    assert.equal(await run('document.documentElement.scrollWidth>innerWidth'),false);
    await click('[aria-label="View selection details"]');await capture(`qa/native-refined-review-${width}.png`);
    assert.equal(await run('document.documentElement.scrollWidth>innerWidth'),false);
  }
  checks.push('Overview and focused review avoid page overflow at desktop and narrow sizes');

  const ax=await cdp('Accessibility.getFullAXTree');
  assert.deepEqual(ax.nodes.filter(n=>!n.ignored&&n.role?.value==='button'&&!n.name?.value).map(n=>n.nodeId),[]);
  checks.push('Rendered buttons expose accessible names');
  await viewport(1710,803);await reset();await run('window.scrollTo(0,0)');await capture('qa/native-refined-overview.png');
  assert.deepEqual(errors,[]);
  const report={passed:true,checks,viewports:[[1710,803],[1440,900],[430,900]],errors};
  await fs.writeFile('qa/native-review-check.json',JSON.stringify(report,null,2));console.log(JSON.stringify(report,null,2));
} finally {browser.close()}
