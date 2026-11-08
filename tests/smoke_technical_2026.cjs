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
 assert.equal(rsi.data.datasets.length,1);
 const change=listeners.get('technical-view:change');
 assert.equal(typeof change,'function');
 $('technical-view').value='cloud';change();
 assert.equal(plots['chart-technical'].data.datasets.length,7);
 assert.match($('t-add').textContent,/반등|분할|추가매수|관망|유보|보류/);
 console.log('PASS: MA5/20/60/120/200, separate RSI and full MACD, cloud toggle, staged entry status');
}).catch(e=>{console.error(e);process.exitCode=1;});
