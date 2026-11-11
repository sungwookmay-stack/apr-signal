/* Verify MA5/20/60/120/200 and separately rendered MACD/RSI. */
const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),{URL}=require('node:url');
const code=fs.readFileSync('assets/app.js','utf8');
const html=fs.readFileSync('index.html','utf8');
const technical=JSON.parse(fs.readFileSync('data/technical.json','utf8'));
technical.series=technical.series.map((x,i)=>({...x,
  ma5:x.ma5??(i>5?x.close:undefined),
  ma120:x.ma120??(i>=120?x.close:undefined)}));
assert.match(html,/id="chart-macd"/);
assert.match(html,/id="chart-rsi"/);
assert.match(html,/id="technical-view"/);
assert.match(html,/id="bottom-stage"/);
assert.match(html,/id="bottom-checks"/);
technical.bottom={date:technical.last.date,stage:'투매 후 반등 탐색 · 바닥 미확인',kind:'early',score:2,max_score:10,data_ready:true,not_prediction:true,checks:[{name:'투매·거래량 급증 확인',passed:true,points:1,max_points:1,detail:'거래량 증가'},{name:'20일선 3거래일 유지',passed:false,points:0,max_points:1,detail:'확인 전'}],washout:{date:'2026-10-30',volume_multiple:4.4,drawdown_from_60d_top_pct:-28.1},reference:{recent_20d_low:231000,recent_20d_low_date:'2026-10-30',ma5:257400,ma20:287025,prior_10d_high_close:330000},latest_confirmed_swing_low:null};
const nodes=new Map(),listeners=new Map(),plots={};
class E{
 constructor(id){this.id=id;this.innerHTML='';this.textContent='';this.value=id==='technical-view'?'ma':'all';this.style={};this.hidden=false;this.dataset={};this.href='';this.classList={toggle(){}};}
 addEventListener(type,fn){listeners.set(this.id+':'+type,fn)}
 getContext(){return {id:this.id}}
}
const $=id=>{if(!nodes.has(id))nodes.set(id,new E(id));return nodes.get(id)};
class Chart{constructor(ctx,opts){this.data=opts.data;plots[ctx.id]=this}destroy(){}}
let ready;
const window={
 APR_BOOTSTRAP:{
  technical,
  market:{series:[],fx:[]},status:{generated_at_utc:'2026-11-09T00:00:00Z'},
  demand:{countries:[{code:'US',name:'미국',amazon:'amazon.com',region:'북미'}],trends:[],amazon:[]},
  news:{items:[]}
 },
 addEventListener(name,fn){if(name==='DOMContentLoaded')ready=fn},
 scrollTo(){}
};
const context=vm.createContext({
 window,location:{hash:'#technical'},document:{getElementById:$,querySelectorAll:()=>[]},
 Chart,URL,console,fetch:async()=>{throw Error('No network in tests')},
 setTimeout:()=>{},clearTimeout:()=>{},alert:()=>{throw Error('Unexpected alert')}
});
vm.runInContext(code,context,{filename:'app.js'});
assert.equal(typeof ready,'function');
ready().then(()=>{
 const trend=plots['chart-technical'],macd=plots['chart-macd'],rsi=plots['chart-rsi'];
 assert(trend,'Moving average chart should render');
 assert(macd,'MACD must be a separate chart from RSI');
 assert(rsi,'RSI must be a separate chart');
 assert.equal(trend.data.datasets.map(x=>x.label).join(','),'종가,MA5,MA20,MA60,MA120,MA200');
 assert.equal(macd.data.datasets.map(x=>x.label).join(','),'MACD선,시그널선,히스토그램');
 assert.equal(macd.data.datasets[2].type,'bar');
 assert.equal(macd.data.datasets[0].type,undefined);
 assert.equal(rsi.data.datasets.length,3);
 assert(plots['chart-volume']);
 assert.doesNotMatch(html,/id="t-risk-price"|분할매수 \/ 물타기 가이드/);
 assert.match($('technical-coverage').textContent,/120거래일/);
 const period=listeners.get('technical-period:change');
 $('technical-period').value='60';period();
 assert.equal(plots['chart-volume'].data.labels.length,60);
 assert.match($('technical-coverage').textContent,/60거래일/);
 $('technical-period').value='all';period();
 assert.equal(plots['chart-volume'].data.labels.length,technical.series.length);
 const change=listeners.get('technical-view:change');
 assert.equal(typeof change,'function');
 $('technical-view').value='cloud';change();
 assert.equal(plots['chart-technical'].data.datasets.length,7);
 assert.match($('t-add').textContent,/반등|분할|추가매수|관망|유보|보류/);
 assert.match($('bottom-stage').textContent,/투매 후 반등 탐색/);
 assert.match($('bottom-score').textContent,/2 \/ 10/);
 assert.match($('bottom-low').textContent,/231,000/);
 assert.match($('bottom-checks').innerHTML,/거래량 급증 확인/);
 console.log('PASS: MA5/20/60/120/200, separate RSI and full MACD, cloud toggle, staged entry status');
}).catch(e=>{console.error(e);process.exitCode=1;});
