/* Offline QA: separated APR scenario page, attribution and provenance. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const financial=JSON.parse(fs.readFileSync('data/financials.json','utf8'));
const market=JSON.parse(fs.readFileSync('data/market.json','utf8'));
const kita=JSON.parse(fs.readFileSync('data/kita_rates.json','utf8'));
const html=fs.readFileSync('index.html','utf8');
const source=fs.readFileSync('assets/sensitivity.js','utf8');
const appSource=fs.readFileSync('assets/app.js','utf8');
assert.match(html,/id="sensitivity"/);
assert.match(html,/data-nav="sensitivity"/);
assert.match(html,/data-mnav="sensitivity"/);
assert.match(html,/assets\/sensitivity\.js/);
assert.match(html,/id="sens-quarter"/);
assert.match(html,/id="sens-sea-share"/);
assert.match(html,/id="sens-fee-pp"/);
assert.match(html,/id="chart-kita-sea"/);
assert.match(appSource,/renderKitaRates/);
assert.doesNotMatch(html.slice(html.indexOf('id="logistics"'),html.indexOf('id="sensitivity"')),/id="freight-share"/);
const nodes=new Map(), events={},charts={};
class MockEl{
 constructor(id){this.id=id;this.value=undefined;this.textContent='';this.innerHTML='';}
 addEventListener(name,fn){events[this.id+':'+name]=fn;}
}
const $=id=>{if(!nodes.has(id))nodes.set(id,new MockEl(id));return nodes.get(id)};
const C={navy:'#293841',teal:'#26756b',purple:'#786a9d'};
const fmt=(n,d=0)=>Number(n).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
const state={financials:financial,market,kitaRates:kita};
const ctx={state,$,C,fmt,escapeHtml:x=>String(x),chart:(name,labels,series,opts)=>{
 charts[name]={labels,series,opts};
}};
const win={};
vm.runInNewContext(source,{window:win,console});
assert(win.APR_SENSITIVITY,'Standalone scenario module should register');
const api=win.APR_SENSITIVITY;
api.init(ctx);
assert.equal($('sens-quarter').value,'2026Q2');
assert.match($('sens-baseline').textContent,/2026Q2/);
assert.match($('sens-baseline').textContent,/565\.5억원/);
assert.match($('sens-op').textContent,/1,905\.5억원/);
assert.match($('sens-opm').textContent,/24\.83%/);
assert.match($('sens-op-delta').textContent,/\+0\.0억원/);
assert.equal(charts['sens-chart'].series[0].values.length,9);
const observedKita = (kita.sea_routes || []).at(-1);
if (observedKita?.feu_usd != null) {
 assert($('sens-kita-note').textContent.includes(observedKita.month), 'Show the observed data month, not a hard-coded old month');
} else {
 assert.match($('sens-kita-note').textContent,/미확인|미수집|확인/);
}
// A new source month must not break the daily collector after it fetched data.
state.kitaRates = {sea_routes:[{month:'2030-01',feu_usd:8500}]};
api.render(ctx);
assert.match($('sens-kita-note').textContent,/2030-01/);
state.kitaRates = kita;
api.render(ctx);
// A positive USD move helps illustrative foreign currency net exposures,
// but this is an assumption, not the issuer's proven currency split.
$('sens-usd').value='10';
events['sens-usd:input']();
assert(Number($('sens-op').textContent.replace(/[^\d.]/g,''))>1905.5);
assert.match($('sens-fx-basis').textContent,/USD\/KRW/);
// Base model and transport share are drawn from the disclosed logistics
// expense; no independent unverified fulfillment amount is invented.
api.applyPreset && api.applyPreset(ctx,'neutral');
$('sens-usd').value='0';
$('sens-sea-change').value='20';
events['sens-sea-change:input']();
assert.match($('sens-op-delta').textContent,/−17\.0억원/);
assert.match($('sens-validation').textContent,/배분 60%/);
// Invalid cumulative allocation must not silently normalize or overspend.
$('sens-sea-share').value='90';
$('sens-air-share').value='35';
events['sens-air-share:input']();
assert.match($('sens-validation').textContent,/100% 초과/);
assert.match($('sens-op').textContent,/계산 보류/);
// Presets act synchronously and reset allocation to valid defaults.
api.init(ctx);
$('sens-preset-neutral').value='button';
events['sens-preset-neutral:click']();
assert.match($('sens-validation').textContent,/가정 검증/);
assert.match($('sens-op-delta').textContent,/\+0\.0억원/);
assert.match($('sens-kita-note').textContent,/자동 대입하지 않습니다/);
console.log('PASS: separate sensitivity tab, verified 2026Q2 inputs, FX, cost bridge, allocation validation, KITA source note');
