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
ready().then(()=>{
  assert.equal(el('sec-latest-date').textContent,'2026-10-28');
  assert.match(el('sec-monitor-status').textContent,/SEC/);
  assert.match(el('sec-last-checked').textContent,/자동 확인 전/);
  const b=el('sec-briefing').innerHTML;
  const f=el('sec-filings').innerHTML;
  const w=el('sec-watchlist').innerHTML;
  assert.match(b,/0\.55%/);
  assert.match(b,/APR 관점/);
  assert.match(f,/485BPOS/);
  assert.match(f,/485BXT/);
  assert.match(f,/485APOS/);
  const related=el('sec-related-manager').innerHTML;
  assert.match(related,/2026-11-05/);
  assert.match(related,/13F-HR/);
  assert.match(related,/CIK 0001409765/);
  assert.match(related,/KBTY 자체 공시 아님/);
  assert.match(related,/신고자/);
  assert.doesNotMatch(f,/2026-11-05/,'13F must not pollute KBTY series filings');
  assert.equal(el('sec-latest-date').textContent,'2026-10-28');
  assert.match(f,/2026-10-28/);
  assert.match(f,/SEC 공시 원문 확인/);
  assert.match(w,/에이피알/);
  assert.match(w,/실제 거래 개시/);
  assert.equal(el('e-apr').textContent,'—','No fabricated APR ETF weight');
  assert.equal(el('e-shares').textContent,'—','No fabricated shares');
  assert.equal(el('e-aum').textContent,'—','No fabricated AUM');
  assert.match(el('sec-filer-link').href,/sec\.gov\/edgar\/browse/);
  console.log('PASS: KBTY SEC Korean filing history, cost, risks and no invented holdings');
}).catch(err=>{console.error(err);process.exitCode=1;});
