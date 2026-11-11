const assert=require('node:assert/strict');
const {forward}=require('../assets/valuation_scenario.js');
assert.equal(forward({price:200000,eps:10000}).per,20);
assert.equal(forward({price:200000,profit100m:4000,shares:40000000,mode:'profit'}).eps,10000);
assert.equal(forward({price:200000,eps:10000,growthPct:25,mode:'growth'}).per,16);
for(const eps of [0,-1,null,NaN,Infinity])assert(forward({price:100,eps}).error);
assert(forward({price:100,profit100m:10,shares:0,mode:'profit'}).error);
assert(forward({price:100,eps:10,growthPct:-100,mode:'growth'}).error);
assert(forward({price:-1,eps:10}).error);
console.log('Forward PER scenario math passed');

const fs=require('node:fs');
assert(fs.readFileSync('.github/workflows/update-and-publish.yml','utf8').includes('assets/valuation_scenario.js'), 'Pages packaging must include forward calculator script');
