/* Regression smoke test: Top100 and per-item ranks must remain visible.
   No real API calls, no external network, no real browser required. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {URL}=require('node:url');
const app=fs.readFileSync('assets/app.js','utf8');
const snapshot=JSON.parse(fs.readFileSync('data/top100.json','utf8'));
const realUS=(snapshot.snapshots||[]).find(x=>x.country==='US'&&x.medicube_confirmed_count>0);
assert(realUS,'Test fixture needs at least one verified U.S. observation.');

function makeTest({includeDemand,includeCharts}){
  const elements=new Map(), listeners=new Map(), charts=[];
  class MockEl {
    constructor(id){this.id=id;this.textContent='';this.innerHTML='';this.style={};this.hidden=false;this.value='';this.dataset={};this.href='';}
    addEventListener(n,fn){listeners.set(this.id+':'+n,fn);}
    getContext(){return {id:this.id};}
  }
  const get=(id)=>{if(!elements.has(id))elements.set(id,new MockEl(id));return elements.get(id);};
  class ChartMock {
    constructor(ctx,config){this.ctx=ctx;this.config=config;charts.push(this);}
    destroy(){}
  }
  const bootstrap={
    top100:snapshot,
    status:{generated_at_utc:'2026-11-04T12:17:45Z'},
    demand:includeDemand?{countries:[{code:'US',name:'미국',region:'북미',amazon:'amazon.com'}],
      amazon:[],trends:[],retailers:[],retail:[],watchlist:[],products:[],api_mode:'free_api_sh'}:undefined
  };
  let ready;
  const win={
    APR_BOOTSTRAP:bootstrap,
    addEventListener(n,fn){if(n==='DOMContentLoaded')ready=fn;},
    scrollTo(){}
  };
  const context=vm.createContext({
    window:win,document:{getElementById:get,querySelectorAll:()=>[]},
    location:{hash:'#demand'},URL,Chart:includeCharts?ChartMock:undefined,
    fetch:async()=>{throw new Error('SIMULATED_OFFLINE');},
    console,setTimeout:()=>{},clearTimeout:()=>{},
    alert:()=>{throw new Error('unexpected alert');}
  });
  vm.runInContext(app,context,{filename:'assets/app.js'});
  assert(ready,'Site must have DOMContentLoaded handler');
  return {ready,get,charts,listeners};
}

async function main(){
  for(const includeDemand of [false,true]){
    for(const includeCharts of [false,true]){
      const x=makeTest({includeDemand,includeCharts});
      await x.ready();
      assert.equal(x.get('amazon-quick-count').textContent,'최소 '+realUS.medicube_confirmed_count+'개',
        'Missing independent leaderboard summary');
      assert.equal(x.get('top100-count').textContent,'최소 '+realUS.medicube_confirmed_count+'개');
      assert.match(x.get('amazon-quick-date').textContent,/2026-11-04/);
      assert.match(x.get('amazon-latest').innerHTML,/B09V7Z4TJG/,
        'Per-product ranking list must show verified ASIN without individual BSR data');
      assert.match(x.get('amazon-latest').innerHTML,/#2/);
      assert.match(x.get('product').innerHTML,/전체 메디큐브 상품/);
      assert.match(x.get('amazon-coverage-detail').textContent,/100개 확인/);
      if(includeCharts){
        for(const id of ['chart-amazon','chart-top100']){
          const call=x.charts.find(z=>z.ctx.id===id);
          assert(call,'Chart missing: '+id);
          assert(call.config.data.datasets.length>0,id+' contains no actual rank data');
          assert.equal(call.config.data.datasets[0].pointRadius,5,
            id+' single date must render a visible dot');
        }
      }
      console.log('PASS: demand='+includeDemand+' chartLibrary='+includeCharts+
        ' summary='+x.get('amazon-quick-count').textContent);
    }
  }
}
main().catch(e=>{console.error(e);process.exitCode=1;});
