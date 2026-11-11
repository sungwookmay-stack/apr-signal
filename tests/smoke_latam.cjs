/* Global Demand Latin America smoke: 3 markets must remain selectable even
   while the large demand dataset has not refreshed. No network/API calls. */
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {URL}=require('node:url');
const app=fs.readFileSync('assets/app.js','utf8');
const nodes=new Map(),callbacks=new Map();
class MockElement{
 constructor(id){this.id=id;this.textContent='';this.innerHTML='';this.style={};this.hidden=false;this.value='all';this.dataset={};this.href='';}
 addEventListener(type,fn){callbacks.set(this.id+':'+type,fn);}
 getContext(){return {id:this.id};}
}
function el(id){if(!nodes.has(id))nodes.set(id,new MockElement(id));return nodes.get(id);}
let ready;
const window={
 APR_BOOTSTRAP:{
  demand:{countries:[{code:'US',name:'미국',region:'북미',amazon:'amazon.com'},
       {code:'CL',name:'칠레',region:'중남미',amazon:null}],
       amazon:[],trends:[],retailers:[],retail:[],watchlist:[],products:[],top100:[]},
  top100:{snapshots:[]},status:{generated_at_utc:'2026-11-05T00:00:00Z'}
 },
 addEventListener(type,fn){if(type==='DOMContentLoaded')ready=fn;},scrollTo(){}
};
const context=vm.createContext({
 window,document:{getElementById:el,querySelectorAll:()=>[]},
 location:{hash:'#demand'},URL,Chart:undefined,console,
 fetch:async()=>{throw Error('OFFLINE');},
 setTimeout:()=>{},clearTimeout:()=>{},alert:()=>{throw Error('unexpected alert');}
});
vm.runInContext(app,context,{filename:'assets/app.js'});
assert.equal(typeof ready,'function');
ready().then(()=>{
 const options=el('country').innerHTML;
 for(const name of ['브라질','아르헨티나','칠레'])assert.ok(options.includes(name),name);
 const region=el('latam-region');
 assert.equal(region.hidden,true,'US country view must hide the LATAM section');
 const menu=el('latam-overview');
 for(const name of ['브라질','아르헨티나','칠레'])assert.ok(menu.innerHTML.includes(name),name);
 function choose(cc){
  const cb=callbacks.get('latam-overview:click');
  assert(cb,'Latin America buttons should be wired');
  cb({target:{closest:()=>({dataset:{latamCountry:cc}})}});
  assert.equal(el('country').value,cc);
 }
 choose('BR');
 assert.equal(region.hidden,false,'Brazil should show the LATAM section');
 assert.match(el('amazon-link').href,/amazon\.com\.br/);
 assert.match(el('top100-url').href,/amazon\.com\.br\/gp\/bestsellers/);
 assert.match(el('top100-count').textContent,/미수집/);
 choose('AR');
 assert.equal(region.hidden,false,'Argentina should show the LATAM section');
 assert.match(el('top100-quality').textContent,/독립 Amazon 마켓/);
 assert.match(el('top100-url').href,/trends\.google\.com/);
 choose('CL');
 assert.equal(region.hidden,false,'Chile should show the LATAM section');
 assert.match(el('top100-quality').textContent,/독립 Amazon 마켓/);
 assert.match(menu.innerHTML,/브라질/);
 for(const code of ['GB','JP','US']){
   el('country').value=code;
   callbacks.get('country:change')();
   assert.equal(region.hidden,true,code+' country view must hide the LATAM section');
 }
 el('country').value='BR';
 callbacks.get('country:change')();
 assert.equal(region.hidden,false,'Switching back to Brazil shows the section again');
 console.log('PASS: BR AR CL selection, no fake Amazon for AR/CL, safe historical fallback');
}).catch(e=>{console.error(e);process.exitCode=1;});
