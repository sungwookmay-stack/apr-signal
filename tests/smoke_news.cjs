/* Offline smoke: Korean news must render as Korean first, preserve original
   title behind a disclosure, and label headline-only summaries honestly. */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {URL} = require('node:url');
const app = fs.readFileSync('assets/app.js', 'utf8');
const nodes = new Map();
const callbacks = new Map();
class MockElement {
  constructor(id) {
    this.id=id;this.innerHTML='';this.textContent='';this.value='all';
    this.dataset={};this.style={};this.hidden=false;this.href='';
  }
  addEventListener(event, fn) {callbacks.set(this.id+':'+event,fn);}
  getContext() {return {id:this.id};}
}
const el = id => {
  if (!nodes.has(id)) nodes.set(id, new MockElement(id));
  return nodes.get(id);
};
let ready;
const window = {
  APR_BOOTSTRAP:{
    news:{
      items:[
        {
          title:'Medicube lanza un nuevo producto - Chile Diario',
          title_ko:'메디큐브, 칠레에서 신제품을 출시했다고 보도',
          summary_ko:'현지 매체가 메디큐브의 신제품 동향을 다뤘습니다.',
          summary_basis:'headline_only',
          publisher:'Chile Diario',
          category:'칠레 스킨부스터',
          country:'CL',
          published:'2026-11-05',
          url:'https://example.com/news'
        },{
          title:'APR Medicube expands US Costco presence - UPI',
          title_ko:'메디큐브, 미국 코스트코 유통 확대',
          summary_ko:'미국 소매점 입점 관련 보도입니다. 판매 실적은 별도 확인이 필요합니다.',
          summary_basis:'headline_only',
          publisher:'UPI',
          category:'미국 오프라인 유통',
          country:'US',
          published:'2026-11-05',
          url:'https://example.com/us-retail'
        },{
          title:'<img src=x onerror=alert(1)> - Bad News',
          category:'KBTY ETF',
          published:'2026-11-04',
          country:'US',
          url:'https://example.com/other'
        }
      ],
      verified_events:[]
    },
    demand:{countries:[{code:'US',name:'미국',amazon:'amazon.com',region:'북미'}],
            amazon:[],trends:[],retailers:[],retail:[],watchlist:[],products:[]},
    status:{generated_at_utc:'2026-11-05T00:00:00Z'}
  },
  addEventListener(event, cb){if(event==='DOMContentLoaded')ready=cb;},
  scrollTo(){}
};
const context=vm.createContext({
  window,document:{getElementById:el,querySelectorAll:()=>[]},
  location:{hash:'#business'},URL,
  fetch:async()=>{throw Error('OFFLINE');},
  console,Chart:undefined,setTimeout:()=>{},clearTimeout:()=>{},
  alert:()=>{throw Error('Unexpected alert');}
});
vm.runInContext(app,context,{filename:'assets/app.js'});
assert.equal(typeof ready,'function');
ready().then(()=>{
  const html=el('news-stack').innerHTML;
  assert.match(html,/메디큐브, 칠레에서 신제품을 출시/);
  assert.match(html,/현지 매체가 메디큐브/);
  assert.match(html,/제목 기반 요약/);
  assert.match(html,/<details class="news-original">/);
  assert.match(html,/Medicube lanza un nuevo producto/);
  assert.match(html,/현지 기사 원문 확인/);
  assert.match(html,/&lt;img src=x onerror=alert\(1\)&gt;/);
  assert.doesNotMatch(html,/<img src=x onerror/);
  assert.match(el('news-korean-status').textContent,/한국어 정리 2\/3건/);
  assert.match(html,/미국 코스트코 유통 확대/);
  el('news-filter').value='미국';
  const update=callbacks.get('news-filter:change');
  assert.equal(typeof update,'function','US filter handler must be registered');
  update();
  const usa=el('news-stack').innerHTML;
  assert.match(usa,/미국 코스트코 유통 확대/);
  assert.doesNotMatch(usa,/메디큐브, 칠레에서 신제품을 출시/);
  assert.doesNotMatch(usa,/Bad News/);
  assert.match(el('news-korean-status').textContent,/한국어 정리 1\/1건/);
  el('news-filter').value='all'; update();
  assert.match(el('news-stack').innerHTML,/메디큐브, 칠레에서 신제품을 출시/);
  assert.match(el('news-stack').innerHTML,/미국 코스트코 유통 확대/);
  console.log('PASS: Korean summary, original source, headline scope, HTML escape');
}).catch(err=>{console.error(err);process.exitCode=1;});
