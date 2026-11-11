/* Pure scenario math. No paid data, implicit forecast or trading instruction. */
(function(root){
'use strict';
function forward({price,eps,profit100m,shares,growthPct=0,mode='eps'}){
 const finite=x=>typeof x==='number'&&Number.isFinite(x);
 if(!finite(price)||price<=0)return {error:'유효한 주가가 필요합니다.'};
 let value=eps;
 if(mode==='profit'){
  if(!finite(profit100m)||!finite(shares)||shares<=0)return {error:'예상 순이익과 0보다 큰 예상 주식수를 입력하세요.'};
  value=profit100m*1e8/shares;
 }else if(mode==='growth'){
  if(!finite(eps)||!finite(growthPct)||growthPct<=-100)return {error:'기준 EPS와 -100%보다 큰 성장률을 입력하세요.'};
  value=eps*(1+growthPct/100);
 }
 if(!finite(value)||value<=0)return {error:'예상 EPS가 0 이하이거나 미입력: PER 산출 불가.'};
 return {eps:value,per:price/value};
}
root.APR_VALUATION={forward};
if(typeof module!=='undefined')module.exports={forward};
})(typeof window!=='undefined'?window:globalThis);
