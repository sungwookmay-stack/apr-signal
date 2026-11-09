/* Independent APR scenario lab. First-order illustrative sensitivity, not forecasts. */
(() => {
'use strict';
const IDS=[
 'sens-revenue','sens-usd','sens-eur','sens-usd-rev','sens-eur-rev',
 'sens-usd-cost','sens-eur-cost','sens-sea-share','sens-air-share',
 'sens-fulfill-share','sens-sea-change','sens-air-change',
 'sens-fulfill-change','sens-recognized','sens-ads','sens-fee-pp',
 'sens-cogs'
];
const START={
 'sens-revenue':0,'sens-usd':0,'sens-eur':0,
 'sens-usd-rev':35,'sens-eur-rev':10,'sens-usd-cost':20,'sens-eur-cost':5,
 'sens-sea-share':25,'sens-air-share':20,'sens-fulfill-share':15,
 'sens-sea-change':0,'sens-air-change':0,'sens-fulfill-change':0,
 'sens-recognized':60,'sens-ads':0,'sens-fee-pp':0,'sens-cogs':0
};
const PRESETS={
 neutral:{},
 freight:{'sens-sea-change':30,'sens-air-change':25,'sens-fulfill-change':10,'sens-usd':5},
 demand:{'sens-revenue':10,'sens-ads':8,'sens-fee-pp':0.3},
 stress:{'sens-revenue':-10,'sens-usd':-5,'sens-eur':-3,
         'sens-sea-change':25,'sens-air-change':20,'sens-ads':5,'sens-cogs':5}
};
let ready=false;
const numeric=(n)=>Number.isFinite(Number(n))?Number(n):null;
function basis(ctx){
 const quarters=ctx.state.financials?.quarterly||[];
 const eligible=quarters.filter(q=>['sales','op','cogs','ads','fees','logistics']
     .every(k=>q[k]!==null&&q[k]!==undefined&&numeric(q[k])!==null&&Number(q[k])>=0));
 const chosen=ctx.$('sens-quarter')?.value;
 return eligible.find(x=>x.period===chosen)||eligible.at(-1)||null;
}
function get(ctx,key){
 const el=ctx.$(key);
 const n=el?numeric(el.value):null;
 return n===null?START[key]:n;
}
function displayControls(ctx){
 const format=(x,key)=>key==='sens-fee-pp'?(x>0?'+':'')+x.toFixed(1)+'%p':
   (x>0&&['sens-revenue','sens-usd','sens-eur','sens-sea-change',
    'sens-air-change','sens-fulfill-change','sens-ads','sens-cogs'].includes(key)?'+':'')+ctx.fmt(x,0)+'%';
 for(const key of IDS)ctx.$(key+'-val')&&(ctx.$(key+'-val').textContent=format(get(ctx,key),key));
}
function number(ctx,x,d=1){return (x>=0?'+':'−')+ctx.fmt(Math.abs(x),d)+'억원'}
function calculate(q,a){
 const revenue=q.sales, op=q.op, totalCost=revenue-op;
 const amount=a['sens-revenue']/100*revenue;
 const unitCostRate=(q.cogs+q.logistics+q.fees)/revenue;
 const demandEBIT=amount*(1-unitCostRate);
 // Revenue/operating-cost FX translation exposures are independent
 // USER assumptions: currency billing and hedges are NOT disclosed.
 const fxRevenue=revenue*(
   a['sens-usd-rev']*a['sens-usd']+a['sens-eur-rev']*a['sens-eur'])/10000;
 const fxCost=totalCost*(
   a['sens-usd-cost']*a['sens-usd']+a['sens-eur-cost']*a['sens-eur'])/10000;
 const recognized=a['sens-recognized']/100;
 const seaCost=q.logistics*a['sens-sea-share']/100*a['sens-sea-change']/100*recognized;
 const airCost=q.logistics*a['sens-air-share']/100*a['sens-air-change']/100*recognized;
 const fulfillCost=q.logistics*a['sens-fulfill-share']/100*a['sens-fulfill-change']/100*recognized;
 const adsCost=q.ads*a['sens-ads']/100;
 const salesNew=revenue+amount+fxRevenue;
 // Base fee rate on incremental sales is already reflected in unitCostRate.
 // This only adds a percentage-POINT change on projected sales.
 const feeCost=salesNew*a['sens-fee-pp']/100;
 const cogsCost=q.cogs*a['sens-cogs']/100;
 const contributions=[
    {name:'판매량·매출 증감 (기본 변동비 차감)',value:demandEBIT},
    {name:'USD/EUR 외화매출 환산',value:fxRevenue},
    {name:'USD/EUR 외화영업비용 환산',value:-fxCost},
    {name:'해상운송 비용',value:-seaCost},
    {name:'항공운송 비용',value:-airCost},
    {name:'현지 풀필먼트 배분 비용',value:-fulfillCost},
    {name:'광고선전비',value:-adsCost},
    {name:'판매수수료율 변화',value:-feeCost},
    {name:'매출원가 상승·하락',value:-cogsCost}
 ];
 const EBITdelta=contributions.reduce((x,item)=>x+item.value,0);
 return {revenue,op,totalCost,salesNew,opNew:op+EBITdelta,
     EBITdelta,unitCostRate,fxRevenue,fxCost,
     contributions,opmBase:100*op/revenue,
     opmNew:100*(op+EBITdelta)/salesNew};
}
function render(ctx){
 const $=ctx.$,fmt=ctx.fmt;
 displayControls(ctx);
 const q=basis(ctx);
 if(!q){
   $('sens-validation').textContent='분기별 매출·영업이익·광고·판매수수료·매출원가·운반비가 모두 확인된 자료가 없습니다.';
   return;
 }
 const a=Object.fromEntries(IDS.map(x=>[x,get(ctx,x)]));
 const shipSum=a['sens-sea-share']+a['sens-air-share']+a['sens-fulfill-share'];
 const revSum=a['sens-usd-rev']+a['sens-eur-rev'];
 const costSum=a['sens-usd-cost']+a['sens-eur-cost'];
 const problems=[];
 if(shipSum>100)problems.push('해상·항공·풀필먼트 배분비중 합계 '+shipSum+'% (100% 초과)');
 if(revSum>100)problems.push('USD+EUR 매출통화 노출 합계 '+revSum+'% (100% 초과)');
 if(costSum>100)problems.push('USD+EUR 영업비용통화 노출 합계 '+costSum+'% (100% 초과)');
 for(const key of IDS)if(!Number.isFinite(a[key]))problems.push('유효하지 않은 입력: '+key);
 if(problems.length){
   $('sens-validation').textContent='입력 조정 필요: '+problems.join(' / ');
   ['sens-op','sens-opm','sens-revenue-out','sens-op-delta','sens-opm-delta'].forEach(id=>$(id).textContent='계산 보류');
   $('sens-breakdown').innerHTML='<tr><td colspan="3">비중 합계가 100%를 넘지 않도록 수정해 주세요.</td></tr>';
   return;
 }
 $('sens-validation').textContent='가정 검증: 통화노출 매출 '+revSum+'%, 비용 '+costSum+
   '% · 운반비 배분 '+shipSum+'% (나머지 '+(100-shipSum)+'%는 비용 충격 미적용)';
 const result=calculate(q,a);
 if(!Number.isFinite(result.opmNew)||result.salesNew<=0){
   $('sens-validation').textContent='시나리오 매출액이 0 이하라 계산할 수 없습니다.';return;
 }
 $('sens-baseline').textContent=q.period+' 확정 공시비용 기준: 매출 '+fmt(q.sales,1)+
   '억원 · 영업이익 '+fmt(q.op,1)+'억원 · 영업이익률 '+fmt(result.opmBase,2)+'% · '+
   '매출원가 '+fmt(q.cogs,1)+'억원 · 운반비 '+fmt(q.logistics,1)+
   '억원 · 판매수수료 '+fmt(q.fees,1)+'억원 · 광고선전비 '+fmt(q.ads,1)+'억원';
 $('sens-revenue-out').textContent=fmt(result.salesNew,1)+'억원';
 $('sens-op').textContent=fmt(result.opNew,1)+'억원';
 $('sens-opm').textContent=fmt(result.opmNew,2)+'%';
 $('sens-op-delta').textContent=number(ctx,result.EBITdelta);
 $('sens-opm-delta').textContent=(result.opmNew-result.opmBase>=0?'+':'−')+
   fmt(Math.abs(result.opmNew-result.opmBase),2)+'%p';
 $('sens-variable-cost').textContent='매출 증분 변동비율 '+fmt(100*result.unitCostRate,1)+
   '% = (공시 매출원가+판매수수료+운반비)/매출 · 광고비 등은 별도 가정';
 const fx=ctx.state.market?.fx?.at(-1)||{};
 $('sens-fx-basis').textContent=
   '환율 기준일 '+(fx.date||'미확인')+' · USD/KRW '+
   (fx.usdkrw!=null?fmt(fx.usdkrw,1):'미수집')+' → 시나리오 '+
   (fx.usdkrw!=null?fmt(fx.usdkrw*(1+a['sens-usd']/100),1):'—')+
   ' / EUR/KRW '+(fx.eurkrw!=null?fmt(fx.eurkrw,1):'미수집')+' → 시나리오 '+
   (fx.eurkrw!=null?fmt(fx.eurkrw*(1+a['sens-eur']/100),1):'—')+
   ' (ECB 참조환율, 분기 실적의 실거래 환율이 아님)';
 const k=ctx.state.kitaRates||{};
 const rows=k.sea_routes||[];
 const latest=rows.at(-1),prev=rows.length>=2?rows.at(-2):null;
 $('sens-kita-note').textContent=latest?.feu_usd!=null?
   'KITA 부산→롱비치 FEU '+latest.month+' $'+fmt(latest.feu_usd)+
   (prev&&prev.feu_usd>0?' (전월대비 '+fmt(100*(latest.feu_usd/prev.feu_usd-1),1)+'%)':'')+
   '. 단일 항로의 시장 참고값으로 APR 전체 해상운임 충격에 자동 대입하지 않습니다.':
   'KITA 해상운임은 실제 확인된 항로만 사용하며, 기업 해상비 비중은 비공개 가정입니다.';
 $('sens-breakdown').innerHTML=result.contributions.map(item=>
   '<tr><td>'+ctx.escapeHtml(item.name)+'</td><td>'+
   number(ctx,item.value)+'</td><td>'+
   (item.value>=0?'영업이익 증가 방향':'영업이익 감소 방향')+'</td></tr>').join('');
 const chartLabels=['매출 증감','외화 매출','외화 비용','해상','항공','풀필먼트','광고비','판매수수료','매출원가'];
 ctx.chart('sens-chart',chartLabels,[
  {label:'가정한 분기 영업이익 증감 (억원)',
    values:result.contributions.map(x=>Number(x.value.toFixed(3))),
    color:ctx.C.teal,background:'rgba(38,117,107,.48)'}
 ],{type:'bar',decimals:1,legend:false,xticks:9});
}
function applyPreset(ctx,preset){
 const data={...START,...(PRESETS[preset]||{})};
 for(const id of IDS){const el=ctx.$(id);if(el)el.value=String(data[id]);}
 render(ctx);
}
function init(ctx){
 if(ready)return;
 const select=ctx.$('sens-quarter');
 const quarters=(ctx.state.financials?.quarterly||[]).filter(
   q=>['sales','op','cogs','ads','fees','logistics'].every(
      k=>q[k]!=null&&numeric(q[k])!==null));
 if(select){
   select.innerHTML=quarters.map(q=>'<option value="'+ctx.escapeHtml(q.period)+'">'+
      ctx.escapeHtml(q.period)+(q.status?.includes('잠정')?' (잠정)':'')+'</option>').join('');
   if(quarters.length)select.value=quarters.at(-1).period;
   select.addEventListener('change',()=>render(ctx));
 }
 for(const key of IDS){
   const el=ctx.$(key);
   if(el)el.addEventListener('input',()=>render(ctx));
 }
 for(const preset of Object.keys(PRESETS)){
   const btn=ctx.$('sens-preset-'+preset);
   if(btn)btn.addEventListener('click',()=>applyPreset(ctx,preset));
 }
 ready=true;
 render(ctx);
}
window.APR_SENSITIVITY={init,render,calculate};
})();