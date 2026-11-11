const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const code = fs.readFileSync('assets/mfds_devices.js','utf8');
const nodes = new Map();
const el = id => {if (!nodes.has(id)) nodes.set(id,{textContent:'',innerHTML:''}); return nodes.get(id);};
let ready;
let response = {schema_version:1,status:'not_configured',records:[]};
let fetchFailed = false;
const context = vm.createContext({
  module:{exports:{}}, document:{getElementById:el},
  window:{addEventListener:(evt,cb)=>{if(evt==='DOMContentLoaded')ready=cb;}},
  fetch:async()=>{if(fetchFailed)throw Error('offline');return {ok:true,json:async()=>response};},
  console
});
vm.runInContext(code, context);
const {render} = context.module.exports;
render(response);
assert.match(el('mfds-status').textContent,/API 연결 전/);
assert.match(el('mfds-count').textContent,/미확인/);
assert.doesNotMatch(el('mfds-count').textContent,/0개/);
assert.match(el('mfds-records').innerHTML,/미허가 판정이 아닙니다/);
const fixture={schema_version:1,status:'ok',current_scan_complete:true,observed_count:1,
  checked_at:'2026-11-11T01:00:00Z',last_success_at:'2026-11-11T01:00:00Z',
  records:[{company:'에이피알',company_match:'public_business_number',
    product:'<img src=x onerror=alert(1)>',model:'synthetic',permit_number:'TEST',
    grade:'4',permit_date:'20200101',registry_changed_at:'20261111',
    first_seen_at:'2026-11-11',presence:'observed',
    cancellation_code_raw:'UNKNOWN_CODE',permitted_use:'<script>alert(1)</script>'}],
  event_history:[{kind:'newly_observed_registry_record',record_key:'test',at:'2026-11-11'}]};
render(fixture);
assert.match(el('mfds-records').innerHTML,/&lt;img/);
assert.doesNotMatch(el('mfds-records').innerHTML,/<img|<script/);
assert.match(el('mfds-records').innerHTML,/국내 판매 범위 미검증/);
assert.match(el('mfds-records').innerHTML,/2020-01-01/);
assert.match(el('mfds-records').innerHTML,/UNKNOWN_CODE/);
assert.match(el('mfds-events').innerHTML,/신규 승인 아님/);
render({...fixture,status:'network_error',current_scan_complete:false,observed_count:null});
assert.match(el('mfds-status').textContent,/최신 조회 실패/);
assert.match(el('mfds-count').textContent,/미확인/);
assert.match(el('mfds-records').innerHTML,/과거 조회 관측/);
assert.doesNotMatch(el('mfds-records').innerHTML,/이번 조회 관측/);
render({...fixture,records:[{...fixture.records[0],presence:'not_observed_in_latest_full_scan'}]});
assert.match(el('mfds-records').innerHTML,/취소 단정 불가/);
render({...fixture,records:[],observed_count:0});
assert.match(el('mfds-count').textContent,/0개 등록정보 관측/);
assert.match(el('mfds-records').innerHTML,/미허가 판정이 아닙니다/);
const html=fs.readFileSync('index.html','utf8');
assert.match(html,/assets\/mfds_devices.js/);
for(const id of ['mfds-status','mfds-count','mfds-dates','mfds-records','mfds-events'])assert(html.includes(`id="${id}"`));
const workflow=fs.readFileSync('.github/workflows/update-and-publish.yml','utf8');
assert.match(workflow,/cp assets\/[^\n]*assets\/mfds_devices.js[^\n]*_site\/assets\//);
assert.match(workflow,/MFDS_DEVICE_API_KEY: \$\{\{ secrets.MFDS_DEVICE_API_KEY \}\}/);
assert.match(workflow,/run: python mfds_device_registry.py/);
assert(!code.includes('serviceKey='));
const initial=JSON.parse(fs.readFileSync('data/mfds_devices.json','utf8'));
assert.equal(initial.schema_version,1);
assert(Array.isArray(initial.records));
assert(!JSON.stringify(initial).includes('FIXTURE-NOT-A-PERMIT'));
assert(!Object.hasOwn(initial,'serviceKey')); // Live snapshots can validly change after activation.
(async()=>{
  await ready();assert.match(el('mfds-status').textContent,/API 연결 전/);
  fetchFailed=true;await ready();assert.match(el('mfds-status').textContent,/로딩 실패/);
  assert.match(el('mfds-count').textContent,/미확인/);
  fetchFailed=false;response=fixture;await ready();
  assert.match(el('mfds-status').textContent,/전체조회 완료/);
  response={};await ready();assert.match(el('mfds-status').textContent,/로딩 실패/);
  console.log('MFDS inactive/failure/observed, escaping, repeated loads and packaging passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
