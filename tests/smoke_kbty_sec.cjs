/* KBTY SEC Korean dashboard smoke: source-grounded, no fabricated APR weight. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {URL} = require('node:url');
const app = fs.readFileSync('assets/app.js', 'utf8');
const sec = JSON.parse(fs.readFileSync('data/kbty_sec.json','utf8'));
const nodes = new Map();
class Node {
  constructor(id){this.id=id;this.innerHTML='';this.textContent='';this.style={};this.hidden=false;this.href='';this.value='all';this.dataset={};}
  addEventListener(){}
  getContext(){return {id:this.id};}
}
const el=id=>{if(!nodes.has(id))nodes.set(id,new Node(id));return nodes.get(id);};
let ready;
const window={
  APR_BOOTSTRAP:{
    kbty:{status:'출시 예정',ticker:'KBTY',aum_usd:null,apr_weight_pct:null,
          apr_shares:null,price_history:[],aum_history:[],holdings:[]},
    kbty_sec:sec,
    status:{generated_at_utc:'2026-11-06T10:00:00Z'}
  },
  addEventListener(event,cb){if(event==='DOMContentLoaded')ready=cb;},
  scrollTo(){}
};
const context=vm.createContext({
  window,document:{getElementById:el,querySelectorAll:()=>[]},
  location:{hash:'#kbty'},URL,
  fetch:async()=>{throw Error('offline-only test');},
  console,Chart:undefined,setTimeout:()=>{},clearTimeout:()=>{},
  alert:()=>{throw Error('Unexpected alert')}
});
vm.runInContext(app,context,{filename:'assets/app.js'});
assert.equal(typeof ready,'function');
ready().then(async()=>{
  assert.equal(el('sec-latest-date').textContent,sec.latest_verified_filing_date);
  assert.match(el('sec-monitor-status').textContent,/SEC/);
  if(sec.last_successful_check_utc)assert.match(el('sec-last-checked').textContent,/UTC/);
  else assert.match(el('sec-last-checked').textContent,/자동 확인 성공 기록 없음/);
  assert.match(el('sec-monitor-status').textContent,/최근 시도/);
  const b=el('sec-briefing').innerHTML;
  const f=el('sec-filings').innerHTML;
  const w=el('sec-watchlist').innerHTML;
  assert.match(b,/0\.55%/);
  assert.match(b,/APR 관점/);
  assert.match(f,/CERT/);
  assert.match(f,/2026-11-10/);
  assert.match(f,/485BPOS/);
  assert.match(f,/485BXT/);
  assert.match(f,/485APOS/);
  assert.ok(!app.includes('sec-related-manager'), 'No unrelated manager filing UI');
  assert.ok(!Object.prototype.hasOwnProperty.call(sec,'related_manager_filings'), 'Only KBTY series disclosures should be stored');
  assert.doesNotMatch(f,/2026-11-05/,'Unrelated 13F must not appear as KBTY filing');
  assert.equal(el('sec-latest-date').textContent,sec.latest_verified_filing_date);
  assert.match(f,/2026-10-28/);
  assert.match(f,/SEC 공시 원문 확인/);
  assert.match(w,/에이피알/);
  assert.match(w,/실제 거래 개시/);
  assert.equal(el('e-apr').textContent,'—','No fabricated APR ETF weight');
  assert.equal(el('e-shares').textContent,'—','No fabricated shares');
  assert.equal(el('e-aum').textContent,'—','No fabricated AUM');
  assert.match(el('sec-filer-link').href,/sec\.gov\/edgar\/browse/);
  sec.last_successful_check_utc=null;
  sec.retrieval_diagnostics=[{endpoint:'SEC submissions',http_status:403}];
  await ready();
  assert.match(el('sec-last-checked').textContent,/성공 기록 없음/);
  assert.match(el('sec-monitor-status').textContent,/HTTP 403/);
  console.log('PASS: KBTY SEC Korean filing history, cost, risks and no invented holdings');
}).catch(err=>{console.error(err);process.exitCode=1;});
