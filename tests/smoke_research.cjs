/* Offline smoke test of APR research pages, no browser API or paid providers. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {URL}=require('node:url');

const read=path=>JSON.parse(fs.readFileSync(path,'utf8'));
const app=fs.readFileSync('assets/app.js','utf8');
const moduleJs=fs.readFileSync('assets/research_dashboard.js','utf8');
const html=fs.readFileSync('index.html','utf8');
const fin=read('data/financials.json');
const market=read('data/market.json');
const reference=read('data/reference_signals.json');
const theses=read('data/apr_theses.json');
const alerts={evaluated_pairs:40,detected_pairs:2,alerts:[
 {country:'US',country_name:'미국',keyword:'medicube',direction:'관심도 상승',
  baseline_avg:23,recent_avg:41,change_pct:78,granularity:'주간',asof:'2026-11-07'},
 {country:'BR',country_name:'브라질',keyword:'AGE-R',direction:'관심도 하락',
  baseline_avg:42,recent_avg:19,change_pct:-55,granularity:'주간',asof:'2026-11-07'}
],source_note:'동일 국가 내 0~100 상대관심도; 실제 판매량 아님'};

assert(html.includes('id="financials"'));
assert(html.includes('id="theses"'));
assert(html.includes('id="trend-alerts"'));
assert(html.includes('./assets/apr_theme.css'));
assert(html.includes('./assets/research_dashboard.js'));

const nodes=new Map(),events={};
class MockEl{
 constructor(id){
  this.id=id;this.innerHTML='';this.textContent='';this.value=id==='fin-table-kind'?'income':'all';
  this.style={};this.hidden=false;this.dataset={};this.href='';this.classList={toggle(){}};
 }
 addEventListener(type,cb){events[this.id+':'+type]=cb;}
 getContext(){return {id:this.id};}
}
const $=id=>{if(!nodes.has(id))nodes.set(id,new MockEl(id));return nodes.get(id);};
class MockChart{
 static instances={};
 constructor(ctx,spec){this.data=spec.data;MockChart.instances[ctx.id]=this;}
 destroy(){}
}
const location={hash:'#financials'};
const window={
 APR_BOOTSTRAP:{
  market,financials:fin,reference_signals:reference,apr_theses:theses,
  trend_signals:alerts,technical:{series:[],last:{}},
  demand:{countries:[
      {code:'US',name:'미국',amazon:'amazon.com',region:'북미'},
      {code:'BR',name:'브라질',amazon:'amazon.com.br',region:'남미'},
      {code:'CL',name:'칠레',amazon:null,region:'남미'},
      {code:'AR',name:'아르헨티나',amazon:null,region:'남미'}],
      trends:[],amazon:[],retail:[],retailers:[],products:[],watchlist:[],top100:[]},
  top100:{snapshots:[]},kbty:{},kbty_sec:{},
  news:{items:[],verified_events:[]},
  status:{generated_at_utc:'2026-11-08T00:00:00Z'}
 },
 addEventListener(type,fn){events['window:'+type]=fn},
 scrollTo(){}
};
const context=vm.createContext({
 window,location,document:{getElementById:$,querySelectorAll:()=>[]},
 URL,Chart:MockChart,console,
 fetch:async()=>{throw Error('offline/no network')},
 setTimeout:()=>{},clearTimeout:()=>{},
 alert:()=>{throw Error('Unexpected alert')}
});
vm.runInContext(moduleJs,context,{filename:'research_dashboard.js'});
vm.runInContext(app,context,{filename:'app.js'});
assert.equal(typeof events['window:DOMContentLoaded'],'function');
events['window:DOMContentLoaded']().then(()=>{
 const matrix=$('fin-table-body').innerHTML;
 const income=MockChart.instances['chart-fin-sales'];
 const per=MockChart.instances['chart-fin-per'];
 const pbr=MockChart.instances['chart-fin-pbr'];
 assert.match(matrix,/2025Q4/);
 assert.match(matrix,/2026Q3/);
 assert.match($('fin-revenue').textContent,/7,731/);
 assert.match($('fin-inventory').textContent,/3,699/);
 assert.equal(income.data.datasets.length,3);
 assert.equal(per.data.datasets.length,6);
 assert.equal(pbr.data.datasets.length,6);
 assert.equal(per.data.datasets[0].label,'실제 원화 종가');
 assert.equal(per.data.datasets[1].label,'PER 15배');
 assert.equal(pbr.data.datasets[1].label,'PBR 5배');
 assert.equal(per.data.datasets[1].data.length,market.series.filter(x=>x.date>='2025-06-01').length);
 const priceDay=market.series.findIndex(x=>x.date>='2025-06-01');
 const day=market.series[priceDay].date;
 const firstEvent=fin.valuation.eps_events.filter(x=>x.available_from<=day).at(-1);
 assert(firstEvent,'At least one TTM earnings event should exist');
 assert.equal(per.data.datasets[1].data[0],Math.round(15*firstEvent.eps_won));
 $('fin-table-kind').value='expenses';
 events['fin-table-kind:change']();
 assert.match($('fin-table-head').innerHTML,/광고선전비/);
 assert.match($('fin-table-body').innerHTML,/1,000/);
 $('fin-table-kind').value='returns';
 events['fin-table-kind:change']();
 assert.match($('fin-table-body').innerHTML,/미산출/);
 location.hash='#theses';events['window:hashchange']();
 assert.match($('thesis-blocks').innerHTML,/재평가 이후에도 저평가인가/);
 assert.match($('thesis-blocks').innerHTML,/미국 수요가 이 속도를 유지하는가/);
 assert.match($('off-ulta-total').textContent,/69개/);
 assert.match($('off-ulta-eligible').textContent,/32개/);
 assert.match($('off-status').innerHTML,/검증 제외/);
 assert.doesNotMatch($('off-status').innerHTML,/<span>104k\+ bought<\/span>/);
 location.hash='#demand';events['window:hashchange']();
 const al=$('trend-alerts').innerHTML;
 assert.match(al,/미국 · medicube/);
 assert.match(al,/브라질 · AGE-R/);
 assert.match(al,/관심도 상승/);
 assert.match(al,/관심도 하락/);
 assert.match($('trend-alert-count').textContent,/감지 2개/);
 console.log('PASS: financial tables, Q4 expenses, PER/PBR point-in-time, retail Target quarantine, country-keyword alerts');
}).catch(e=>{console.error(e);process.exitCode=1;});
