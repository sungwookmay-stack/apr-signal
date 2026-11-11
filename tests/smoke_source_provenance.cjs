const assert=require('node:assert/strict'),fs=require('fs'),vm=require('vm');
const window={};vm.runInNewContext(fs.readFileSync('assets/research_dashboard.js','utf8'),{window});
const f=[
 {date:'2025-01-01',reporter:'old',type:'elestock',ownership_pct:10},
 {date:'2026-10-01',reporter:'new',type:'majorstock',ownership_pct:20},
 {date:'2026-11-01',reporter:'new',type:'elestock',ownership_pct:1},
 {date:'2026-09-01',reporter:'new',type:'elestock',ownership_pct:0.5},
 {date:'2026-12-01',reporter:'missing',type:'elestock',ownership_pct:null}
];
const series=window.APR_RESEARCH.ownershipSeries(f);
assert.equal(series.latest.reporter,'new');
assert.equal(series.latest.type,'elestock');
assert.equal(JSON.stringify(series.points),JSON.stringify([{date:'2026-09-01',value:0.5},{date:'2026-11-01',value:1}]));
assert.equal(window.APR_RESEARCH.ownershipSeries([]).points.length,0);
const html=fs.readFileSync('index.html','utf8');
assert(html.includes('15059612/openapi.do'));
assert(!html.includes('대차 수치는 키움 REST ka20068 또는 KSD 공식 API'));
assert(html.includes('NAV·APR 비중·보유주식수: 수동 검증 CSV 입력'));
assert(html.includes('AUM 잔액 추이'));
console.log('PASS: ownership reporter/type aligned, actual lending provider, ETF automation scope');
