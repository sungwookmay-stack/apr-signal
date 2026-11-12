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
if(!flows.flow_last_date)assert.match($('flow-total-label').textContent,/판정 보류/);
else assert.notEqual($('flow-total-label').textContent,'');
assert.match($('flow-summary-body').innerHTML,/연기금/);
assert.match($('flow-external-reference').innerHTML,/2차 집계/);
assert.match($('flow-external-reference').innerHTML,/−538억원/);
if(!flows.lending?.last_date)assert.match($('flow-loan-date').textContent,/미수집/);
if(!flows.short?.last_date)assert.equal($('flow-short-ratio').textContent,'—');
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

const approx=state.flows;
const lastday=approx.daily.at(-1);
lastday.amount_estimated=true;
lastday.foreign_net_qty=12;
lastday.foreign=12*240000;
approx.latest_daily=lastday;
approx.data_status.naver_flow_is_estimated=true;
approx.data_status.naver_public_result={status:'ok',rows:80,pages:8};
approx.actors.foreign.windows['5'].estimated_value_days=5;
mod.render(ctx);
assert.match($('flow-policy').textContent,/종가/);
assert.match($('flow-summary-body').innerHTML,/≈/);
assert.match($('flow-latest-daily').textContent,/추정금액/);
assert.match($('flow-collection-status').textContent,/투자자 수급: 네이버 보조자료\(KRX 시장\) ok 80거래일/);
console.log('PASS: APR four investor flow groups, 5/20/60, unknown pension, source-labeled reference, short and KSD null handling');

// Date-lag reference is explicit; today remains withheld.
state.flows={...state.flows,flow_last_date:dates.at(-2),
 asof_analysis:{date:dates.at(-2),lag_price_sessions:1,
 actors:state.flows.actors,combined:{label:'참고 분석',detail:'이전일'}}};
mod.render(ctx);
assert.match($('flow-total-label').textContent,/현재일 판정 보류/);
assert.match($('flow-asof-detail').textContent,/1거래일 차이/);
assert(!charts['flow-cum-chart'].labels.includes(last.slice(5)));
// Lending fields have separate units/meaning and missing observations are null.
state.flows.lending={last_date:dates.at(-1),latest:{date:dates.at(-1),returned_qty:0,new_qty:10,balance_qty:500}};
state.flows.lending_daily=[{date:dates.at(-3),returned_qty:100,new_qty:20,balance_qty:490},
 {date:dates.at(-1),returned_qty:0,new_qty:10,balance_qty:500}];
mod.render(ctx);
const repayment=charts['flow-lending-trades-chart'].series[0].values;
assert.equal(repayment.at(-1),0);
assert.equal(repayment.at(-2),null);
assert.equal(repayment.at(-3),100);
assert.equal(charts['flow-lending-balance-chart'].series[0].values.at(-1),500);
assert.match($('flow-lending-coverage').textContent,/관측 2일/);
assert.match($('flow-lending-body').innerHTML,/상환|500주/);
state.flows.lending={};state.flows.lending_daily=[];mod.render(ctx);
assert.equal(charts['flow-lending-trades-chart'].labels.length,0);
assert.match($('flow-lending-coverage').textContent,/미수집/);

// Missing short data has explicit state, no empty percentage axis, and is not zero.
state.flows.short={};state.flows.short_daily=[];mod.render(ctx);
assert.match($('flow-short-status').textContent,/수집 실패.*0이 아니라 미확인/);
assert.equal($('flow-short-graph').hidden,true);
assert.equal($('flow-short-empty').hidden,false);
assert.match($('flow-short-source-status').textContent,/KRX 원본 미확보/);
// True observed zero is valid; returning from missing state shows graph again.
state.flows.short={last_date:last,latest:{short_volume_ratio_pct:0}};
state.flows.short_daily=[{date:last,short_volume_ratio_pct:0}];mod.render(ctx);
assert.equal($('flow-short-ratio').textContent,'0.00%');
assert.equal($('flow-short-graph').hidden,false);
assert.equal($('flow-short-empty').hidden,true);
assert.equal(charts['flow-short-chart'].series[0].values[0],0);
state.flows.short_daily=[];mod.render(ctx);
assert.equal($('flow-short-graph').hidden,true);
