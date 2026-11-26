/* Offline smoke test of APR research pages, no browser API or paid providers. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {URL}=require('node:url');

const read=path=>JSON.parse(fs.readFileSync(path,'utf8'));
const app=fs.readFileSync('assets/app.js','utf8');
const sensitivityJs=fs.readFileSync('assets/sensitivity.js','utf8');
const kita=read('data/kita_rates.json');
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
  market,financials:fin,reference_signals:reference,apr_theses:theses,kita_rates:kita,
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
vm.runInContext(sensitivityJs,context,{filename:'sensitivity.js'});
vm.runInContext(app,context,{filename:'app.js'});
assert.equal(typeof events['window:DOMContentLoaded'],'function');
events['window:DOMContentLoaded']().then(()=>{
 const matrix=$('fin-table-body').innerHTML;
 const income=MockChart.instances['chart-fin-sales'];
 const per=MockChart.instances['chart-fin-per'];
 const pbr=MockChart.instances['chart-fin-pbr'];
 const perUSD=MockChart.instances['chart-fin-per-usd'];
 const pbrUSD=MockChart.instances['chart-fin-pbr-usd'];
 assert.match(matrix,/2025Q4/);
 assert.match(matrix,/2026Q3/);
 assert.match($('fin-revenue').textContent,/7,731/);
 assert.ok($('fin-inventory').textContent.includes(Math.round(fin.balance.at(-1).inventory).toLocaleString('en-US')));
 assert.equal(income.data.datasets.length,3);
 assert.equal(per.data.datasets.length,6);
 assert.equal(pbr.data.datasets.length,6);
 assert.equal(perUSD.data.datasets.length,6);
 assert.equal(pbrUSD.data.datasets.length,6);
 assert.equal(html.match(/assets\/research_dashboard\.js/g)?.length,1);
 assert.equal(html.match(/assets\/apr_theme\.css/g)?.length,1);
 assert.equal(per.data.datasets[0].label,'실제 원화 종가');
 assert.equal(per.data.datasets[1].label,'PER 15배');
 assert.equal(pbr.data.datasets[1].label,'PBR 5배');
 assert.equal(per.data.datasets[1].data.length,market.series.filter(x=>x.date>='2025-06-01').length);
 const priceDay=market.series.findIndex(x=>x.date>='2025-06-01');
 const day=market.series[priceDay].date;
 const firstEvent=fin.valuation.eps_events.filter(x=>x.available_from<=day).at(-1);
 assert.equal(firstEvent.period,'2025Q1');
 assert.equal(per.data.datasets[1].data[0],Math.round(firstEvent.eps_won*15));
 const gap=market.series.filter(x=>x.date>='2025-06-01').findIndex(x=>x.date>='2025-08-15'&&x.date<'2025-11-15');
 assert(gap>=0);
 assert.equal(per.data.datasets[1].data[gap],null,'Excluded new EPS must block stale prior EPS');
 assert(pbr.data.datasets[1].data[gap]>0,'Book remains independently usable');
 const series=market.series.filter(x=>x.date>='2025-06-01');
 const beforeQ3=series.findIndex(x=>x.date==='2026-11-13');
 const afterQ3=series.findIndex(x=>x.date==='2026-11-16');
 assert(beforeQ3>=0 && afterQ3>=0);
 assert.equal(per.data.datasets[1].data[beforeQ3],Math.round(11545.69*15));
 assert.equal(pbr.data.datasets[1].data[beforeQ3],Math.round(17309.45*5));
 assert.equal(per.data.datasets[1].data[afterQ3],Math.round(12494.84*15));
 assert.equal(pbr.data.datasets[1].data[afterQ3],Math.round(17736.04*5));
 assert.equal(per.data.datasets[0].data.at(-1),series.at(-1).close_krw);
 assert.equal(pbr.data.datasets[0].data.at(-1),series.at(-1).close_krw);
 assert.match($('fin-primary-rows').innerHTML,/6,913/);
 assert.match($('fin-primary-rows').innerHTML,/181/);
 assert.match($('fin-valuation-note').textContent,/지배주주/);
 assert.match($('fin-anchor-detail').textContent,/주식수/);
 assert(!html.includes('forward-per-panel'));
 assert(!html.includes('valuation_scenario.js'));
 assert(!moduleJs.includes('APR_VALUATION'));
 assert(!('forward' in fin.valuation));
 assert(!fs.existsSync('assets/valuation_scenario.js'));
 assert(!fs.readFileSync('.github/workflows/update-and-publish.yml','utf8').includes('valuation_scenario.js'));
 assert(!fs.readFileSync('.github/workflows/pr-checks.yml','utf8').includes('smoke_valuation.cjs'));

 $('fin-table-kind').value='expenses';
 events['fin-table-kind:change']();
 assert.match($('fin-table-head').innerHTML,/광고선전비/);
 assert.match($('fin-table-body').innerHTML,/1,000/);
 $('fin-table-kind').value='returns';
 events['fin-table-kind:change']();
 assert.match($('fin-table-body').innerHTML,/미산출/);
 location.hash='#theses';events['window:hashchange']();
 assert.match($('thesis-blocks').innerHTML,/이익 성장보다 주가가 앞서가지는 않는가/);
 assert.match($('thesis-blocks').innerHTML,/미국 온·오프라인 수요의 지속성/);
 assert.match($('thesis-blocks').innerHTML,/thesis-sparkline/,'Historical watchpoints should show trends');
 location.hash='#demand';events['window:hashchange']();
 // Saved observations change independently of UI releases. Verify against the
 // input data, then use fixed fixtures to independently test the arithmetic.
 const savedRetail=reference.retail;
 const total=savedRetail.find(x=>x.metric==='catalog_items');
 const online=savedRetail.find(x=>x.metric==='online_only_items');
 assert.equal($('off-ulta-total').textContent,total?Number(total.value).toLocaleString('en-US')+'개':'—');
 assert.equal($('off-ulta-online').textContent,online?Number(online.value).toLocaleString('en-US')+'개':'—');
 assert.equal($('off-ulta-eligible').textContent,
   total&&online&&total.date===online.date?Math.max(0,total.value-online.value).toLocaleString('en-US')+'개':'—');
 for(const fixture of [
   {total:70,online:38,date:'2030-01-01',onlineDate:'2030-01-01',expected:'32개'},
   {total:83,online:12,date:'2030-01-02',onlineDate:'2030-01-02',expected:'71개'},
   {total:83,online:12,date:'2030-01-02',onlineDate:'2030-01-01',expected:'—'},
   {total:0,online:0,date:'2030-01-03',onlineDate:'2030-01-03',expected:'0개'},
   {total:20,online:null,date:'2030-01-04',expected:'—'},
   {total:null,online:null,expected:'—'}
 ]){
   reference.retail=savedRetail.filter(x=>!['catalog_items','online_only_items'].includes(x.metric));
   if(fixture.total!==null)reference.retail.push({retailer:'ulta',metric:'catalog_items',value:fixture.total,date:fixture.date});
   if(fixture.online!==null)reference.retail.push({retailer:'ulta',metric:'online_only_items',value:fixture.online,date:fixture.onlineDate});
   events['window:hashchange']();
   assert.equal($('off-ulta-total').textContent,fixture.total===null?'—':fixture.total+'개');
   assert.equal($('off-ulta-eligible').textContent,fixture.expected);
 }
 reference.retail=savedRetail;
 events['window:hashchange']();
 assert.match($('off-status').innerHTML,/검증 제외/);
 assert.match($('retailer-statements').innerHTML,/유통사 공식 발표/);
 assert.doesNotMatch($('off-status').innerHTML,/<span>104k\+ bought<\/span>/);
 const al=$('trend-alerts').innerHTML;
 assert.match(al,/미국 · medicube/);
 assert.match(al,/브라질 · AGE-R/);
 assert.match(al,/관심도 상승/);
 assert.match(al,/관심도 하락/);
 assert.match($('trend-alert-count').textContent,/감지 2개/);
 // KITA market reference rates are leading signals; the separate
 // sensitivity tab uses disclosed APR baselines and explicit user assumptions.
 $('freight-group').value='long';
 location.hash='#logistics';events['window:hashchange']();
 assert.match($('freight-route-table').innerHTML,/중동/);
 assert.match($('freight-route-table').innerHTML,/베트남/);
 assert.equal(MockChart.instances['chart-sea'].data.datasets.length,4);
 assert.equal(MockChart.instances['chart-kita-sea'].data.datasets.length,2);
 const latestRoute=(data,destination)=>(data.sea_routes||[])
   .filter(r=>r.origin==='Busan'&&r.destination===destination&&r.month)
   .sort((a,b)=>a.month.localeCompare(b.month)).at(-1);
 const assertKitaDisplay=data=>{
   const west=latestRoute(data,'Long Beach'),east=latestRoute(data,'New York');
   assert.equal($('kita-feu').textContent,west?.feu_usd!=null?'$'+Number(west.feu_usd).toLocaleString('en-US'):'—');
   assert.equal($('kita-asof').textContent,
     'KITA 미 서안 '+(west?.month||'미수집')+' / 미 동안 '+(east?.month||'미수집')+
     ' · 시장참고 USD/FEU, 공시 조건·할증료에 유의');
 };
 assertKitaDisplay(kita);
 const savedKitaRoutes=kita.sea_routes;
 // Deterministic rollover, changed price, independent route lag and missing data.
 for(const fixture of [
   {sea_routes:[{origin:'Busan',destination:'Long Beach',month:'2030-01',feu_usd:9100},
                {origin:'Busan',destination:'New York',month:'2030-01',feu_usd:10200}]},
   {sea_routes:[{origin:'Busan',destination:'Long Beach',month:'2030-02',feu_usd:9200},
                {origin:'Busan',destination:'New York',month:'2030-01',feu_usd:10200}]},
   {sea_routes:[]}
 ]){
   kita.sea_routes=fixture.sea_routes;
   events['window:hashchange']();
   assertKitaDisplay(fixture);
 }
 kita.sea_routes=savedKitaRoutes;
 events['window:hashchange']();
 $('freight-group').value='near';events['freight-group:change']();
 assert.equal(MockChart.instances['chart-sea'].data.datasets.length,3);
 location.hash='#sensitivity';events['window:hashchange']();
 // A new filing should advance this view without requiring the test to be edited.
 const latestComplete=fin.quarterly
   .filter(q=>['sales','op','cogs','ads','fees','logistics']
     .every(k=>q[k]!=null&&Number.isFinite(Number(q[k]))&&Number(q[k])>=0))
   .sort((a,b)=>a.period.localeCompare(b.period)).at(-1);
 assert.ok(latestComplete,'Expected a complete disclosed quarter in the saved data');
 const ko=(value,places)=>Number(value).toLocaleString('ko-KR',
   {minimumFractionDigits:places,maximumFractionDigits:places});
 assert.ok($('sens-baseline').textContent.startsWith(latestComplete.period+' '));
 assert.equal($('sens-op').textContent,ko(latestComplete.op,1)+'억원');
 assert.equal($('sens-opm').textContent,ko(100*latestComplete.op/latestComplete.sales,2)+'%');
 assert.match($('sens-kita-note').textContent,/롱비치/);
 $('sens-sea-change').value='20';events['sens-sea-change:input']();
 const seaShock=latestComplete.logistics*0.25*0.20*0.60;
 assert.equal($('sens-op-delta').textContent,(seaShock>0?'−':'+')+ko(seaShock,1)+'억원');
 $('sens-preset-neutral').value='button';events['sens-preset-neutral:click']();
 assert.match($('sens-op-delta').textContent,/\+0\.0억원/);
 console.log('PASS: financial tables, Q4 expenses, PER/PBR point-in-time, retail Target quarantine, country-keyword alerts and KITA leading rates with separate sensitivity tab');
}).catch(e=>{console.error(e);process.exitCode=1;});
