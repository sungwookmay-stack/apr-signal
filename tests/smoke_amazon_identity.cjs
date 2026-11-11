/* Offline DOM regression: partial identity, diagnostics and historical fallback. */
const assert=require('node:assert/strict'),fs=require('node:fs'),vm=require('node:vm');
const nodes=new Map();
const el=id=>{if(!nodes.has(id))nodes.set(id,{textContent:'',innerHTML:'',style:{},addEventListener(){}});return nodes.get(id);};
const ctx=vm.createContext({window:{addEventListener(){}},document:{getElementById:el,querySelectorAll:()=>[]},console,URL,Chart:undefined});
vm.runInContext(fs.readFileSync('assets/app.js','utf8').replace("window.addEventListener('DOMContentLoaded',init);", "window.test={state,renderTop100};"),ctx);
vm.runInContext(`const {state,renderTop100}=window.test;state.country='US';state.demand={countries:[{code:'US',amazon:'amazon.com'}]};state.top100={snapshots:[{country:'US',date:'2026-11-11',coverage_count:100,rank_coverage_complete:true,identity_coverage_count:74,unidentified_count:26,medicube_confirmed_count:4,medicube_listings:[],identity_diagnostics:{pages:[{status:'normalized',missing_card_rows:20,empty_card_identity_rows:0,cached_identity_rows:7,rejected_rank_rows:1}]}}]};renderTop100();`,ctx);
assert.match(el('top100-quality').textContent,/제목 또는 브랜드 식별 74\/100/);
assert.match(el('top100-quality').textContent,/응답 카드 미포함 20건/);
assert.match(el('top100-count').textContent,/최소 4/);
vm.runInContext(`delete state.top100.snapshots[0].identity_diagnostics;renderTop100();`,ctx);
assert.match(el('top100-quality').textContent,/다음 수집부터/);
vm.runInContext(`state.top100.snapshots=[];renderTop100();`,ctx);
assert.doesNotMatch(el('top100-quality').textContent,/카드 미포함/);
console.log('PASS Amazon identity diagnostics, historical fallback, empty/repeated views');
