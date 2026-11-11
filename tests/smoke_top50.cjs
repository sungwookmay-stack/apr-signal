/* Smoke: real saved Top100 observation renders even when per-item API data is absent. */

const assert=require('node:assert/strict');
const fs=require('node:fs'),vm=require('node:vm'),{URL}=require('node:url');
const app=fs.readFileSync('assets/app.js','utf8');
const original={snapshots:['US','GB'].map(country=>({country,observed_at_utc:'2026-11-09T22:30:00Z',date:'2026-11-09T22:30:00Z',verified_count:0,candidate_count:1,items:[{rank:5,asin:'B000000001',title:'medicube cream',brand_status:'title_candidate',movement:'first_observation',rank_change:null}],exited:[]}))};
const snapshots=original.snapshots||[];
function latest(cc){return snapshots.filter(x=>x.country===cc).sort((a,b)=>a.date.localeCompare(b.date)).at(-1);}
assert(latest('US'),'Saved US category observation required for this smoke fixture.');
function countText(s){return '확정 '+s.verified_count+' · 후보 '+s.candidate_count;}
function buildApp({withDemand,withCharts}){
  const elements=new Map(),callbacks=new Map(),charts=[];
  class Element{
    constructor(id){this.id=id;this.textContent='';this.innerHTML='';this.style={};this.hidden=false;this.value='';this.dataset={};this.href='';}
    addEventListener(n,fn){callbacks.set(this.id+':'+n,fn);}
    getContext(){return {id:this.id};}
  }
  const el=(id)=>{if(!elements.has(id))elements.set(id,new Element(id));return elements.get(id);};
  class MockChart{constructor(ctx,config){this.ctx=ctx;this.config=config;charts.push(this);}destroy(){}}
  const bootstrap={top50:original,status:{generated_at_utc:'2026-11-04T00:00:00Z'}};
  if(withDemand)bootstrap.demand={countries:[
    {code:'US',name:'미국',region:'북미',amazon:'amazon.com'},
    {code:'GB',name:'영국',region:'유럽',amazon:'amazon.co.uk'}
  ],amazon:[],trends:[],retailers:[],retail:[],watchlist:[],products:[],api_mode:'free_api_sh'};
  let onready;
  const window={APR_BOOTSTRAP:bootstrap,addEventListener(n,fn){if(n==='DOMContentLoaded')onready=fn;},scrollTo(){}};
  const ctx=vm.createContext({window,document:{getElementById:el,querySelectorAll:()=>[]},
    location:{hash:'#demand'},URL,Chart:withCharts?MockChart:undefined,
    fetch:async()=>{throw Error('OFFLINE');},console,setTimeout:()=>{},clearTimeout:()=>{},
    alert:()=>{throw Error('unexpected alert');}});
  vm.runInContext(app,ctx,{filename:'assets/app.js'});
  return {ready:onready,el,callbacks,charts};
}
async function check(){
 for(const withDemand of [true,false])for(const withCharts of [true,false]){
  const a=buildApp({withDemand,withCharts});
  await a.ready();
  for(const cc of ['US','GB']){
    if(cc==='GB'){
      assert.match(a.el('country').innerHTML,/영국/,'UK must be selectable even if demand file failed');
      a.el('country').value='GB';
      a.callbacks.get('country:change')();
    }
    const s=latest(cc);
    if(!s)continue;
    assert.match(a.el('amazon-coverage-detail').textContent,/제목 표기 후보/);
    if(s.items.length){
      assert.ok(a.el('top100-items').innerHTML.includes(s.items[0].asin));
      assert.ok(a.el('product').innerHTML.includes('선택 브랜드 전체 상품'));
    }
    if(withCharts&&s.items.length){
      for(const id of ['chart-amazon','chart-top100']){
        const chart=a.charts.filter(z=>z.ctx.id===id).at(-1);
        assert(chart,id+' should render verified rankings');
        assert(chart.config.data.datasets.length>0,id+' must not be empty');
        const n=snapshots.filter(x=>x.country===cc).length;
        assert.equal(chart.config.data.datasets[0].pointRadius,n===1?5:0);
      }
    }
  }
  console.log('PASS: demand='+withDemand+', chart='+withCharts);
 }
}
check().catch(e=>{console.error(e);process.exitCode=1;});
