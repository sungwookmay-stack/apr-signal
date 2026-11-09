/* Offline flow UI regression: no missing-as-zero, no pension double count. */
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm');
const flows=JSON.parse(fs.readFileSync('data/flows.json','utf8'));
const flowReference=JSON.parse(fs.readFileSync('data/flow_reference.json','utf8'));
const market=JSON.parse(fs.readFileSync('data/market.json','utf8'));
const html=fs.readFileSync('index.html','utf8');
const moduleCode=fs.readFileSync('assets/flows.js','utf8');
const app=fs.readFileSync('assets/app.js','utf8');
assert(html.includes('data-page="flows"'));
assert(html.includes('data-nav="flows"'));
assert(html.includes('data-mnav="flows"'));
assert(html.includes('src="./assets/flows.js'));
assert(html.includes('flow-loan-return'));
assert(html.includes('flow-short-position'));
assert(app.includes("'flow_reference'"));
assert(app.includes("if(state.nav==='flows'"));

const nodes=new Map(),events={};const charts={};
class E{
 constructor(id){this.id=id;this.textContent='';this.innerHTML='';this.value=id==='flow-period'?'20':'';}
 addEventListener(event,callback){events[this.id+':'+event]=callback;}
}
const $=id=>{if(!nodes.has(id))nodes.set(id,new E(id));return nodes.get(id);};
const state={
 flows,flowReference,market,
 technical:{bottom:{stage:'투매 후 반등 탐색 · 바닥 미확인',date:'2026-11-06'}}
};
const ctx={$,state,
 fmt:(v,d=0)=>Number(v).toLocaleString('ko-KR',
   {minimumFractionDigits:d,maximumFractionDigits:d}),
 escapeHtml:v=>String(v),
 validLink:v=>v,
 chart:(id,labels,series)=>{charts[id]={labels,series}},
 C:{navy:'#111',teal:'#222',purple:'#333',orange:'#444',red:'#555'}
};
const window={};vm.runInNewContext(moduleCode,{window,console});
const mod=window.APR_FLOWS;assert(mod);
mod.init(ctx);
assert.match($('flow-total-label').textContent,/판정 보류/);
assert.match($('flow-summary-body').innerHTML,/연기금/);
assert.match($('flow-external-reference').innerHTML,/2차 집계/);
assert.match($('flow-external-reference').innerHTML,/−538억원/);
assert.match($('flow-loan-date').textContent,/미수집/);
assert.equal($('flow-short-ratio').textContent,'—');
assert.equal(charts['flow-cum-chart'].series.length,4);
const last=market.series.at(-1).date;
const dates=market.series.slice(-20).map(x=>x.date);
state.flows={
 ...flows,flow_last_date:last,price_last_date:last,price_aligned:true,
 actors:{
  foreign:{label:'순매수 개선',level:'positive',windows:{
   '5':{net_krw:1000000000},'20':{net_krw:3000000000},'60':null
  }},
  institution:{label:'매도 우위',level:'weak',windows:{
   '5':{net_krw:-100000000},'20':{net_krw:-200000000},'60':null
  }},
  pension:{label:'확인 대기',level:'unknown',windows:{
   '5':null,'20':null,'60':null
  }},
  individual:{label:'매도',level:'weak',windows:{
   '5':{net_krw:-600000000},'20':{net_krw:-2900000000},'60':null
  }}
 },
 combined:{label:'주요 수급 엇갈림 · 확인 대기',detail:'동행 확인 필요'},
 daily:dates.map(d=>({date:d,foreign:150000000,institution:-10000000,
      pension:null,individual:-140000000})),
 latest_daily:{date:last,foreign:150000000,institution:-10000000,pension:null,individual:-140000000}
};
mod.render(ctx);
assert.match($('flow-total-label').textContent,/엇갈림/);
assert.match($('flow-summary-body').innerHTML,/\+30\.0억원/);
assert.match($('flow-summary-body').innerHTML,/−2\.0억원/);
assert.match($('flow-summary-body').innerHTML,/연기금/);
assert.match($('flow-summary-body').innerHTML,/—/);
assert.equal(charts['flow-cum-chart'].series[2].values.at(-1),null);
$('flow-period').value='5';events['flow-period:change']();
assert.equal(charts['flow-cum-chart'].labels.length,5);
assert.match($('flow-latest-daily').textContent,/외국인/);
console.log('PASS: APR four investor flow groups, 5/20/60, unknown pension, source-labeled reference, short and KSD null handling');
