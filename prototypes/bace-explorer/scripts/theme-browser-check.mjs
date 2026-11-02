import fs from 'node:fs/promises';
import assert from 'node:assert/strict';
import {openBrowser} from './cdp-browser.mjs';

const b=await openBrowser('http://127.0.0.1:4173/?case=demo');
const samples=[];
const settle=async()=>{await b.moveAway();await b.sleep(160)};
// Measure actual computed foregrounds against composited ancestor backgrounds.
const sample=async selector=>{
  const result=await b.run(`(()=>{
    const e=document.querySelector(${JSON.stringify(selector)});
    if(!e)throw Error('Missing contrast sample');
    const rgba=s=>s.match(/[\\d.]+/g).map(Number);
    const over=(a,b)=>a.slice(0,3).map((v,i)=>v*(a[3]??1)+b[i]*(1-(a[3]??1)));
    const background=e=>e?over(rgba(getComputedStyle(e).backgroundColor),background(e.parentElement)):[255,255,255];
    const bg=background(e),fg=over(rgba(getComputedStyle(e).color),bg);
    const lum=c=>c.map(v=>{v/=255;return v<=.04045?v/12.92:((v+.055)/1.055)**2.4}).reduce((n,v,i)=>n+v*[.2126,.7152,.0722][i],0);
    const a=lum(fg),z=lum(bg);
    return {selector:${JSON.stringify(selector)},ratio:(Math.max(a,z)+.05)/(Math.min(a,z)+.05),background:bg,foreground:fg};
  })()`);
  assert.ok(result.ratio>=4.5,`${selector}: text contrast ${result.ratio.toFixed(2)}`);
  samples.push(result);
};
const darkSurface=async selector=>{
  const rgb=await b.run(`getComputedStyle(document.querySelector(${JSON.stringify(selector)})).backgroundColor.match(/[\\d.]+/g).slice(0,3).map(Number)`);
  assert.ok(Math.max(...rgb)<80,`${selector} leaked a light surface`);
};
try{
  await b.viewport(1712,1104);await b.waitFor('document.querySelector("[data-node-id=dc1]")');
  await b.run('document.fonts.ready.then(()=>true)');await settle();
  assert.equal(await b.run('getComputedStyle(document.documentElement).colorScheme'),'dark');
  for(const selector of ['.paper-copy','.column-header h2','.node-short','.evidence-card h3','.demo-badge'])await sample(selector);
  await b.click('[data-node-id="dc1"]');await b.click('[data-testid="set-a"]');
  await b.click('[aria-label="Focus set 1 in graph"]');await settle();
  for(const selector of ['.disclosure-span.is-active','.dc-node.is-active .node-short','.dc-node.is-muted .node-short','.supported','.ec-full-text','.set-name'])await sample(selector);
  const strokes=await b.run(`['dc1-ec1','dc1-ec6'].map(id=>getComputedStyle(document.querySelector('[data-edge="'+id+'"]')).stroke)`);
  assert.notEqual(strokes[0],strokes[1],'Support and candidate edges must remain visually distinct');
  const gray=strokes[1].match(/[\d.]+/g).map(Number);
  assert.ok(Math.max(...gray)-Math.min(...gray)<25,'Candidate selection must remain neutral');
  await b.run('window.scrollTo(0,0)');await b.capture('qa/carbon-demo.png');
  await b.click('[aria-label="Filter graph"]');await settle();
  await darkSurface('.filter-popover');await sample('.filter-popover .toggle-label');
  await b.capture('qa/carbon-filter.png');await b.key('Escape');
  await b.click('.ec-sources>button');await settle();
  await darkSurface('.document-reader');await sample('.reader-copy');await sample('.reader-toolbar');
  await b.capture('qa/carbon-reader.png');await b.key('Escape');
  assert.equal(await b.run('document.querySelector(".set-button").ariaExpanded'),'true');
  await b.click('[data-node-id="dc2"]');await settle();
  await sample('.unsupported');await sample('.diagnosis-rationale');
  await b.click('[aria-label="View selection details"]');await b.capture('qa/carbon-diagnosis.png');
  await b.viewport(430,900);await b.click('[aria-label="View selection details"]');
  assert.equal(await b.run('document.documentElement.scrollWidth>innerWidth'),false);
  await b.capture('qa/carbon-narrow.png');
  assert.deepEqual(b.errors,[]);
  const report={passed:true,scope:'Selected text contrast and dark surface consistency; not full accessibility conformance',minimumTextContrast:Math.min(...samples.map(s=>s.ratio)),samples,errors:b.errors};
  await fs.writeFile('qa/carbon-theme-check.json',JSON.stringify(report,null,2));
  console.log(JSON.stringify(report,null,2));
}finally{b.close()}
