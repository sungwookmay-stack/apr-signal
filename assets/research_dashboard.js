/* APR SIGNAL · Financial / valuation / offline research UI.
   No external services or implied actual POS data. Depends on the
   source-labeled JSON snapshots already maintained by APR SIGNAL. */
(function (global) {
'use strict';

const safeArr=v=>Array.isArray(v)?v:[];
const num=v=>typeof v==='number'&&Number.isFinite(v)?v:null;
const last=a=>a.length?a[a.length-1]:null;
const asPct=v=>num(v)==null?'—':v.toFixed(1)+'%';
const asNum=(v,fmt,d=1)=>num(v)==null?'—':fmt(v,d);
const row=a=>a.join(' · ');

function renderTrends(ctx){
 const {state,$,escapeHtml,fmt}=ctx;
 const d=state.trendSignals, e=$('trend-alerts');if(!e)return;
 const count=$('trend-alert-count'),note=$('trend-note');
 if(!d || !Number.isFinite(d.evaluated_pairs)){
   e.innerHTML='<p class="subtle">유의미한 변화 분석이 아직 실행되지 않았습니다. 다음 정기 수집 시 확인합니다.</p>';
   if(count)count.textContent='분석 대기';
   return;
 }
 const list=safeArr(d.alerts);
 // Show at most two strongest signals per country to prioritize geographic spread.
 const countries={};
 const featured=list.filter(x=>{
  countries[x.country]=(countries[x.country]||0)+1;
  return countries[x.country]<=2;
 }).slice(0,12);
 if(count)count.textContent='분석 '+fmt(d.evaluated_pairs)+'개 키워드 조합 · 감지 '+list.length+'개 · 국가별 대표 최대 2개';
 if(note)note.textContent='판정 기준: 최근 평균이 기준기간보다 8p 이상 및 상승 +35%/하락 -30% 이상, 변동성·지속성 필터 통과. '+(d.source_note||'검색 관심도는 실제 판매량이 아닙니다.');
 e.innerHTML=featured.length?featured.map(x=>
   '<button type="button" class="trend-alert" data-trend-country="'+escapeHtml(x.country||'')+'">'+
   '<span class="trend-alert-heading"><b>'+escapeHtml(x.country_name||x.country)+' · '+escapeHtml(x.keyword||'')+'</b><em class="'+(x.direction==='관심도 상승'?'trend-up':'trend-down')+'">'+escapeHtml(x.direction||'')+'</em></span>'+
   '<span class="trend-alert-values">기준 '+asNum(x.baseline_avg,fmt,1)+' → 최근 '+asNum(x.recent_avg,fmt,1)+' / 100 · 변화 '+(num(x.change_pct)!=null&&x.change_pct>0?'+':'')+asNum(x.change_pct,fmt,1)+'% · '+escapeHtml(x.asof||'')+'</span>'+
   '<small>'+escapeHtml(x.granularity||'')+' 관측 · 동일 국가·검색어 기준 · 자료 확인</small></button>'
 ).join(''):'<p class="subtle">설정한 유의미한 변화 기준을 충족한 국가·검색어가 없습니다. 이는 검색량이 감소하지 않았다는 뜻은 아닙니다.</p>';
}

function latestRelease(events,date,amount){
 const list=safeArr(events).filter(x=>x.available_from<=date && num(x[amount])>0);
 return last(list.sort((a,b)=>String(a.available_from).localeCompare(String(b.available_from))));
}

function renderFinancials(ctx){
 const {state,$,chart,escapeHtml,fmt,C,validLink}=ctx;
 const f=state.financials||{};
 const q=safeArr(f.quarterly),b=safeArr(f.balance),r=safeArr(f.roe_ttm);
 const latestQ=last(q),latestB=last(b);
 const set=(id,value)=>{const el=$(id);if(el)el.textContent=value};
 const fn=(v,d=1)=>asNum(v,fmt,d);
 set('fin-revenue',latestQ?fn(latestQ.sales,0)+'억':'—');
 set('fin-revenue-period',latestQ?latestQ.period+' · '+latestQ.status:'공시 데이터 확인 필요');
 set('fin-opm',latestQ?asPct(latestQ.op_margin_pct):'—');
 set('fin-opm-period',latestQ?latestQ.period+' 연결 기준':'자료 확인 중');
 set('fin-inventory',latestB?fn(latestB.inventory,0)+'억':'—');
 set('fin-inventory-period',latestB?latestB.period+' 기준':'미공개');
 set('fin-turnover',latestB?fn(latestB.reported_inventory_turnover,1)+'회':'—');
 set('fin-turnover-period',latestB?latestB.asof+' 공시상 연환산':'미공개');

 if(!q.length){
   const el=$('fin-table-body');if(el)el.innerHTML='<tr><td colspan="8">연결 재무데이터를 아직 불러오지 못했습니다.</td></tr>';
   return;
 }
 const dates=q.map(x=>x.period);
 chart('chart-fin-sales',dates,[
  {label:'매출액 (억)',values:q.map(x=>x.sales),color:C.navy,background:'#193a5a'},
  {label:'영업이익 (억)',values:q.map(x=>x.op),color:C.teal,background:'#0b917f'},
  {label:'순이익 (억)',values:q.map(x=>x.ni),color:C.orange,background:'#bf8854'}
 ],{type:'bar',legend:true});
 chart('chart-fin-margins',dates,[
  {label:'영업이익률 (%)',values:q.map(x=>x.op_margin_pct),color:C.teal},
  {label:'순이익률 (%)',values:q.map(x=>x.net_margin_pct),color:C.orange},
  {label:'광고비율 (%)',values:q.map(x=>x.ads_ratio_pct),color:C.purple}
 ],{legend:true,decimals:1});
 chart('chart-fin-inventory',b.map(x=>x.period),[
  {label:'재고자산 (억)',values:b.map(x=>x.inventory),color:C.navy},
  {label:'재고/자산 (%)',values:b.map(x=>x.inventory_assets_pct),color:C.orange,axis:'y1'}
 ],{legend:true,y1:true});
 chart('chart-fin-expense',dates,[
  {label:'광고선전비율 (%)',values:q.map(x=>x.ads_ratio_pct),color:C.purple},
  {label:'판매수수료율 (%)',values:q.map(x=>x.selling_fee_ratio_pct),color:C.teal},
  {label:'운반비율 (%)',values:q.map(x=>x.shipping_ratio_pct),color:C.orange}
 ],{legend:true,decimals:1});
 chart('chart-fin-cfo',dates,[
  {label:'영업현금흐름 (억)',values:q.map(x=>x.cfo),color:C.teal},
  {label:'연결 순이익 (억)',values:q.map(x=>x.ni),color:C.navy},
  {label:'FCF 참고 (억)',values:q.map(x=>x.fcf_proxy),color:C.orange}
 ],{legend:true});
 chart('chart-fin-roe',r.map(x=>x.period),[
  {label:'TTM ROE (%)',values:r.map(x=>x.roe_ttm_pct),color:C.teal}
 ],{decimals:1});

 const schemas={
  income:{cols:['분기','확정 상태','매출','영업이익','순이익','영업이익률'],
    items:q,keys:['period','status','sales','op','ni','op_margin_pct'],percent:['op_margin_pct']},
  expenses:{cols:['분기','판관비','광고선전비','판매수수료','운반비','광고비율','수수료율','운반비율'],
    items:q,keys:['period','sga','ads','fees','logistics','ads_ratio_pct','selling_fee_ratio_pct','shipping_ratio_pct'],
    percent:['ads_ratio_pct','selling_fee_ratio_pct','shipping_ratio_pct']},
  balance:{cols:['기준일','재고자산','총자산','매출채권','재고/자산','회전율'],
    items:b,keys:['asof','inventory','assets','receivables','inventory_assets_pct','reported_inventory_turnover'],
    percent:['inventory_assets_pct'],times:['reported_inventory_turnover']},
  cashflow:{cols:['분기','현금흐름(CFO)','순이익','유형자산 취득','FCF 참고치','현금전환율'],
    items:q,keys:['period','cfo','ni','capex','fcf_proxy','cash_conversion_pct'],percent:['cash_conversion_pct']},
  returns:{cols:['기준일','최근 12개월 ROE','산출 기준','ROIC'],
    items:r,keys:['asof','roe_ttm_pct','method','roic'],percent:['roe_ttm_pct']}
 };
 const selector=$('fin-table-kind')?.value||'income',cfg=schemas[selector]||schemas.income;
 const head=$('fin-table-head'),body=$('fin-table-body');
 if(head)head.innerHTML='<tr>'+cfg.cols.map(x=>'<th>'+escapeHtml(x)+'</th>').join('')+'</tr>';
 if(body)body.innerHTML=cfg.items.map(x=>'<tr>'+cfg.keys.map(key=>{
   const v=x[key];
   let val=v===null||v===undefined?'—':typeof v==='number'?
      (cfg.percent?.includes(key)?asPct(v):cfg.times?.includes(key)?fn(v,1)+'회':fn(v,2)):
       escapeHtml(String(v));
   if(key==='roic')val='미산출 · 투하자본 내역 검증 필요';
   return '<td>'+val+'</td>';
 }).join('')+'</tr>').join('')||'<tr><td colspan="8">동일 기준 검증 자료가 없습니다.</td></tr>';
 set('fin-table-footnote',selector==='returns'?
     'ROE는 시점이 일치하는 기초·기말 자본 및 TTM 순이익이 있을 때만 산출. ROIC는 검증된 영업투하자본 계산 전 미산출.':
     '2025년 4분기는 사업보고서 연간−3분기 누계. 2026년 3분기 비용 상세는 정식 분기보고서 확인 전까지 공란. 단위 억원.');
 const src=$('fin-sources');
 if(src)src.innerHTML='출처: 2025년 사업보고서(연간)와 2025년 3분기 누계, 2026년 1분기·반기보고서. '+
   '<a target="_blank" rel="noopener noreferrer" href="https://apr-in.aprd.io/annual_report/%5B%EC%97%90%EC%9D%B4%ED%94%BC%EC%95%8C%5D%EC%82%AC%EC%97%85%EB%B3%B4%EA%B3%A0%EC%84%9C_2025%EB%85%84.pdf">2025년 사업보고서 ↗</a> · '+
   '<a target="_blank" rel="noopener noreferrer" href="https://apr-in.com/ir.php?year=2025">2025년 4Q IR ↗</a>';

 const history=safeArr(state.market?.series).filter(x=>x.date>='2025-06-01' && num(x.close_krw)>0);
 const prices=history.map(x=>x.close_krw), labels=history.map(x=>x.date);
 const usd=history.map(x=>num(x.close_usd));
 chart('chart-fin-krw',labels,[{label:'KRW 종가',values:prices,color:C.navy}],{decimals:0,legend:false});
 chart('chart-fin-usd',labels,[{label:'USD 환산종가',values:usd,color:C.teal}],{decimals:2,legend:false});
 const start=history.length?history[0].date:'미수집';
 set('fin-price-date',history.length?'관측 '+start+' ~ '+last(history).date:'과거 일봉 미수집');
 const valuation=f.valuation||{},eps=safeArr(valuation.eps_events),book=safeArr(valuation.book_events);
 const multiplesPER=safeArr(valuation.per_multiples),multiplesPBR=safeArr(valuation.pbr_multiples);
 function bands(items,key,multiples,id,name){
  const arr=history.map(x=>{
    const a=latestRelease(items,x.date,key);
    return a?a[key]:null;
  });
  const series=[{label:'실제 원화 종가',values:prices,color:C.navy,width:3}];
  const colors=[C.grey,C.orange,C.teal,C.purple,C.red];
  multiples.forEach((mult,i)=>series.push({
   label:name+' 대리 '+mult+'배',
   values:arr.map(v=>num(v)>0?Math.round(v*mult):null),
   color:colors[i%colors.length],width:1
  }));
  chart(id,labels,series,{decimals:0,legend:true,xticks:5});
 }
 bands(eps,'eps_won',multiplesPER,'chart-fin-per','PER');
 bands(book,'bps_won',multiplesPBR,'chart-fin-pbr','PBR');
 function usdBands(events,key,multiples,id,name){
  const base=history.map(x=>{const a=latestRelease(events,x.date,key);
    return a&&num(a[key])>0&&num(x.usdkrw)>0?a[key]/x.usdkrw:null;});
  const datasets=[{label:'실제 달러 환산 종가',values:history.map(x=>x.close_usd??null),color:C.navy,width:3}];
  const colors=[C.grey,C.orange,C.teal,C.purple,C.red];
  multiples.forEach((m,i)=>datasets.push({
    label:name+' 대리 '+m+'배 (USD)',color:colors[i%colors.length],width:1,
    values:base.map(x=>num(x)==null?null:Math.round(x*m*100)/100)
  }));
  chart(id,labels,datasets,{decimals:2,legend:true,xticks:5});
 }
 usdBands(eps,'eps_won',multiplesPER,'chart-fin-per-usd','PER');
 usdBands(book,'bps_won',multiplesPBR,'chart-fin-pbr-usd','PBR');
 const dartFin=state.dartFinancials||{};
 set('dart-financials-status',dartFin.status||
    'OpenDART 공식 연결재무 공시 수집 전 · 기존 분기보고서 확정자료 유지');
 set('dart-financials-count',Array.isArray(dartFin.filings)?dartFin.filings.length+'개 정기보고서 확인':'DART 조회 전');

 const note=$('fin-valuation-note');
 if(note){
  const missingJune=history.length&&history[0].date>'2025-06-09';
  note.textContent='PER·PBR 대리 밴드: 연결 순이익·총자본과 저장 주식수 기준입니다. 지배주주 이익·지분 및 가중평균·희석·자기주식 조정은 검증되지 않아 표준 PER/PBR과 다를 수 있습니다. '+
    '밴드 배수는 고정 시나리오이며 역사적 평균·분위수나 목표주가가 아닙니다. DART 자동 수집값이 밴드 입력을 자동 교체하지는 않습니다. '+
    '2024 EPS/자본은 확인한 비교보고서 공개일인 2025-08-14 이후, 2025 연간 확정이익은 2026-03-23 이후에만 적용합니다. 그 이전 빈 구간은 미검증이며 0이 아닙니다. '+
    '달러 밴드는 해당 거래일의 원화 밴드 ÷ USD/KRW입니다.';

 }
 const current=last(history);
 const anchor=current?latestRelease(eps,current.date,'eps_won'):null;
 const capital=current?latestRelease(book,current.date,'bps_won'):null;
 set('fin-anchor-detail', '주가 기준일 '+(current?.date||'없음')+' · EPS '+(anchor?fmt(anchor.eps_won,2)+'원 / 재무 '+anchor.asof+' / 적용 '+anchor.available_from+' / 주식수 '+fmt(anchor.shares,0)+'주 / '+anchor.source:'확인 전')+
   ' · BPS '+(capital?fmt(capital.bps_won,2)+'원 / 총자본 '+fmt(capital.equity_100m,2)+'억원 / 재무 '+capital.asof+' / 적용 '+capital.available_from:'확인 전'));
 const audit=f.dart_reconciliation||{};
 set('fin-audit-summary',(audit.note||'DART 독립 대조 전')+' · 수집 '+(audit.checked_at_utc||'미확인'));
 const auditBody=$('fin-audit-rows');
 if(auditBody)auditBody.innerHTML=safeArr(audit.rows).map(x=>'<tr><td>'+escapeHtml(x.period)+'</td><td>'+escapeHtml(x.account==='equity'?'연결 총자본':'연결 순이익')+'</td><td>'+asNum(x.input_100m,fmt,2)+'</td><td>'+asNum(x.dart_100m,fmt,2)+'</td><td>'+escapeHtml(x.status==='match_rounding'?'반올림 범위 일치':x.status==='mismatch'?'불일치: 확인 필요':'독립 미검증')+(/^https:\/\/dart\.fss\.or\.kr\/dsaf001\/main\.do\?rcpNo=\d{14}$/.test(x.source_url||'')?' <a href="'+x.source_url+'" target="_blank" rel="noopener noreferrer">공시</a>':'')+'</td></tr>').join('');
 const ids=['price','eps','profit','shares','growth','mode','horizon','source'];
 const field=k=>$('forward-'+k);
 const priceField=field('price');
 if(priceField && !priceField.dataset.initialized){priceField.value=current?.close_krw??'';priceField.dataset.initialized='1';}
 const read=k=>{const raw=String(field(k)?.value??'').trim();return raw===''?null:Number(raw);};
 const calculate=()=>{
   if(!global.APR_VALUATION)return;
   const mode=field('mode')?.value||'eps';
   const r=global.APR_VALUATION.forward({price:read('price'),eps:mode==='growth'?anchor?.eps_won:read('eps'),profit100m:read('profit'),shares:read('shares'),growthPct:read('growth'),mode});
   set('forward-result',r.error||((field('horizon')?.value||'선택 기간')+' · 예상 EPS '+fmt(r.eps,2)+'원 · Forward PER '+fmt(r.per,2)+'배 · '+(mode==='growth'?'TTM 성장률 단순 가정':(field('source')?.value||'추정 근거 미입력: 검증되지 않은 사용자 가정'))));
 };
 ids.forEach(k=>{if(field(k))field(k).oninput=calculate;});
 calculate();

}

function renderRetail(ctx){
 const {state,$,chart,escapeHtml,fmt,C,validLink}=ctx;
 const r=state.reference||{},f=state.financials||{},d=state.demand||{},t=state.trendSignals||{};
 const metrics=safeArr(r.retail),history=safeArr(r.retail_history),amazonWeeks=safeArr(r.amazon_weekly);
 const find=name=>metrics.find(x=>x.metric===name);
 const ulta=find('catalog_items'),online=find('online_only_items'),target=find('brand_catalog_items');
 const set=(id,text)=>{const e=$(id);if(e)e.textContent=text;};
 set('off-ulta-total',ulta?fmt(ulta.value)+'개':'—');
 set('off-ulta-date',ulta?ulta.date+' 출처확인':'미수집');
 set('off-ulta-online',online?fmt(online.value)+'개':'—');
 const eligible=ulta&&online&&ulta.date===online.date?
     Math.max(0,ulta.value-online.value):null;
 set('off-ulta-eligible',eligible===null?'—':fmt(eligible)+'개');
 set('off-target-total',target?fmt(target.value)+'개':'미수집');
 set('off-target-date',target?target.date+' 전체 브랜드 기준':'브랜드 전체 SKU는 검증 전');
 const h=history.filter(x=>x.value!=null&&x.eligible_for_trend!==false);
 const dates=[...new Set(h.map(x=>x.date))].sort();
 chart('chart-off-retail',dates,[
   {label:'Ulta 등록 SKU',values:dates.map(date=>h.find(x=>x.metric==='catalog_items'&&x.date===date)?.value??null),color:C.navy},
   {label:'Ulta Online Only',values:dates.map(date=>h.find(x=>x.metric==='online_only_items'&&x.date===date)?.value??null),color:C.orange},
   {label:'Target 브랜드 SKU',values:dates.map(date=>h.find(x=>x.metric==='brand_catalog_items'&&x.date===date)?.value??null),color:C.teal}
 ],{legend:true});
 const aw=amazonWeeks.slice().sort((a,b)=>String(a.week).localeCompare(String(b.week)));
 const reviews=safeArr(r.product_review_history).filter(x=>x.reviews_count!=null && x.verified);
 const reviewsDates=[...new Set(reviews.map(x=>x.date))].sort();
 const products=[...new Set(reviews.map(x=>x.product_id))].slice(0,4);
 chart('chart-off-reviews',reviewsDates,products.map((id,i)=>({
   label:((reviews.find(x=>x.product_id===id)?.retailer||'')+' · '+(reviews.find(x=>x.product_id===id)?.label||id)),
   values:reviewsDates.map(day=>reviews.find(x=>x.product_id===id&&x.date===day)?.reviews_count??null),
   color:[C.teal,C.navy,C.orange,C.purple][i]
 })),{decimals:0,legend:true});
 const el=$('off-status');
 if(el)el.innerHTML=metrics.map(x=>{
   const stale=String(x.metric||'').endsWith('_bought_lower');
   const verified=x.eligible_for_trend!==false&&!stale;
   return '<div class="off-signal"><strong>'+escapeHtml(x.label||x.metric)+'</strong>'+
     '<span>'+escapeHtml(verified?(x.display||String(x.value)):'검증 제외')+'</span>'+
     '<small>'+escapeHtml(x.retailer||'')+' · '+escapeHtml(x.date||'')+
       (verified?' · 확인된 화면 관측':' · 품목 연계 미확인/추이 제외')+'</small>'+
     '<p>'+escapeHtml(x.scope||'')+'</p></div>';
 }).join('')||'<p class="subtle">오프라인 대리지표 수집 전입니다.</p>';
 const warning=$('off-target-warning'),err=safeArr(r.collection?.failures);
 if(warning)warning.textContent='Target: '+(err.some(s=>String(s).startsWith('target:'))?
    '최근 자동 수집 실패. 과거 브랜드/카테고리 수를 혼합하지 않고 검증 전 구매 배지의 추이 계산도 제외합니다.':
    '최신 브랜드 페이지에서 확인된 SKU만 사용합니다.')+
  ' 점포별 POS 매출·실제 재주문은 공개 관측치가 아닙니다.';

 const reviewLatest=safeArr(r.product_review_history).filter(x=>x.verified).sort((a,b)=>String(a.date).localeCompare(String(b.date))).at(-1);
 const summary=$('off-review-status');
 if(summary)summary.textContent=reviewLatest?
   '최근 검증된 상품 리뷰: '+reviewLatest.label+' · '+reviewLatest.reviews_count+'건 · '+reviewLatest.date+
   ' (온라인 소비자 반응, 점포별 판매량 아님) · 조회 상태 '+Object.entries(r.product_review_status?.source_results||{}).map(([k,v])=>k.split('_')[0]+': '+v).join(' / '):
   '상품별 리뷰·평점의 일관된 공식 관측자료를 확보하면 추이를 표시합니다. 조회 차단/누락 시 임의값을 채우지 않습니다.';
 const statements=$('retailer-statements');
 if(statements)statements.innerHTML=safeArr(r.retailer_statements).slice().sort((a,b)=>String(b.date).localeCompare(String(a.date))).map(x=>
   '<article class="retailer-statement"><small>'+escapeHtml(x.date||'')+
   ' · '+escapeHtml(x.retailer||'')+' · '+(x.source_type==='official_retailer_newsroom'?'유통사 공식 발표':'독립 현지 언론 보도')+'</small>'+
   '<strong>'+escapeHtml(x.title||'')+'</strong>'+
   '<p>'+escapeHtml(x.summary_ko||'')+'</p>'+
   '<a href="'+validLink(x.source_url||'')+'" target="_blank" rel="noopener noreferrer">원문 확인 ↗</a></article>'
 ).join('')||'<p class="subtle">검증된 유통사 관련 발표를 아직 확보하지 못했습니다.</p>';
}
function ownershipSeries(filings){
 const ordered=safeArr(filings).filter(x=>x.reporter&&x.type&&num(x.ownership_pct)!=null)
   .slice().sort((a,b)=>String(b.date).localeCompare(String(a.date))||String(b.receipt_no||'').localeCompare(String(a.receipt_no||'')));
 const latest=ordered[0];
 return {latest,points:latest?ordered.filter(x=>x.reporter===latest.reporter&&x.type===latest.type)
   .reverse().map(x=>({date:x.date,value:x.ownership_pct})):[]};
}
function renderTheses(ctx){
 const {state,$,chart,escapeHtml,fmt,C}=ctx;
 const r=state.reference||{},f=state.financials||{},d=state.demand||{},t=state.trendSignals||{};
 const metrics=safeArr(r.retail),amazonWeeks=safeArr(r.amazon_weekly);
 const find=name=>metrics.find(x=>x.metric===name);
 const ulta=find('catalog_items'),online=find('online_only_items'),target=find('brand_catalog_items');
 const qq=safeArr(f.quarterly),latestQ=last(qq),priorQ=qq.length>1?qq[qq.length-2]:null;
 const latestB=last(safeArr(f.balance)),roe=last(safeArr(f.roe_ttm));
 const stock=last(safeArr(state.market?.series));
 const eps=stock?latestRelease(safeArr(f.valuation?.eps_events),stock.date,'eps_won'):null;
 const bps=stock?latestRelease(safeArr(f.valuation?.book_events),stock.date,'bps_won'):null;
 const per=stock&&eps?stock.close_krw/eps.eps_won:null,pbr=stock&&bps?stock.close_krw/bps.bps_won:null;
 const usTop=last(safeArr(state.top100?.snapshots).filter(x=>x.country==='US').sort((a,b)=>a.date.localeCompare(b.date)));
 const yoy=latestQ?.sales_yoy_pct;
 const insider=ownershipSeries(state.dartOwnership?.filings);
 const map={
  per:per?fmt(per,1)+'배 (TTM 참고)':'EPS 기준 미확인',
  pbr:pbr?fmt(pbr,1)+'배 (최근 공시 BPS)':'BPS 기준 미확인',
  revenue_yoy:num(yoy)!=null?(yoy>=0?'+':'')+fmt(yoy,1)+'% · '+latestQ.period:'전년 동기 비교 미확인',
  roe:roe?fmt(roe.roe_ttm_pct,1)+'% · '+roe.period:'비교 자본 자료 미확인',
  insider:insider.latest?insider.latest.reporter+' · '+insider.latest.ownership_pct+'% ('+insider.latest.date+') · '+(insider.latest.type_label||insider.latest.type)+' · 동일 보고자·유형 이력':'OpenDART 신규 공시 확인 전',
  opm:latestQ?fmt(latestQ.op_margin_pct,1)+'% ('+latestQ.period+')'+
     (priorQ?' · QoQ '+fmt(latestQ.op_margin_pct-priorQ.op_margin_pct,1)+'%p':''):'자료 미확인',
  ads:latestQ?.ads_ratio_pct!=null?fmt(latestQ.ads_ratio_pct,1)+'%':qq.length>1?fmt(qq[qq.length-2].ads_ratio_pct,1)+'% ('+qq[qq.length-2].period+')':'미공개',
  fees:latestQ?.selling_fee_ratio_pct!=null?fmt(latestQ.selling_fee_ratio_pct,1)+'%':qq.length>1?fmt(qq[qq.length-2].selling_fee_ratio_pct,1)+'% ('+qq[qq.length-2].period+')':'미공개',
  freight:latestQ?.shipping_ratio_pct!=null?fmt(latestQ.shipping_ratio_pct,1)+'%':qq.length>1?fmt(qq[qq.length-2].shipping_ratio_pct,1)+'% ('+qq[qq.length-2].period+')':'미공개',
  inventory:latestB?fmt(latestB.inventory,0)+'억 · '+fmt(latestB.reported_inventory_turnover,1)+'회 ('+latestB.period+')':'재고 자료 미확인',
  cfo:latestQ?.cash_conversion_pct!=null?fmt(latestQ.cash_conversion_pct,1)+'%':qq.length>1?fmt(qq[qq.length-2].cash_conversion_pct,1)+'% ('+qq[qq.length-2].period+')':'미공개',
  fx:stock?.usdkrw?fmt(stock.usdkrw,1)+'원 ('+stock.fx_usd_date+')':'환율 미수집',
  costco:'약 400개 매장 · 2026년 10월 보도',
  ulta:ulta?fmt(ulta.value)+' SKU · '+ulta.date:'공식 SKU 미수집',
  target:target?fmt(target.value)+'개 (브랜드 전체)':'브랜드 전체 SKU 미수집 · 과거 카테고리 지표 별도',
  amazon:usTop?(Number(usTop.medicube_confirmed_count)>0?'최소 '+fmt(usTop.medicube_confirmed_count)+'개':'진입 여부 미확인')+' ('+usTop.date+')':'Beauty Top100 미수집',
  trends:safeArr(t.alerts).some(x=>x.country==='US')?safeArr(t.alerts).filter(x=>x.country==='US').map(x=>x.keyword+' '+x.direction).join(', '):'미국에서 기준을 충족한 유의미 변화 미감지 또는 자료 부족',
  reorders:'공식 POS·재주문 수량 미공개',
  reviews:(()=>{const items=safeArr(r.product_review_history).filter(x=>x.verified).sort((a,b)=>String(a.date).localeCompare(String(b.date)));const recent=items.at(-1);return recent?recent.retailer+' '+recent.reviews_count+'건 · '+recent.rating+'점 ('+recent.date+')':'공식 상품 상세페이지 첫 확인 전';})(),
  retailer_statement:safeArr(r.retailer_statements).length?'공식 발표·현지 보도 '+r.retailer_statements.length+'건 분리 확인':'확인된 발표 없음'
 };
 const fn=safeArr(f.quarterly),bn=safeArr(f.balance);
 const mkt=safeArr(state.market?.series);
 const retailHist=safeArr(r.retail_history).filter(x=>x.eligible_for_trend!==false);
 const priceSnapshot=(key)=>mkt.filter(x=>x.close_krw>0).map(x=>({
   date:x.date, value:(()=>{
    const el=latestRelease(safeArr(f.valuation?.[key==='per'?'eps_events':'book_events']),x.date,
                   key==='per'?'eps_won':'bps_won');
    return el?.[key==='per'?'eps_won':'bps_won']>0?
      x.close_krw/el[key==='per'?'eps_won':'bps_won']:null;
   })()
 })).filter(x=>num(x.value)!=null);
 function observations(id){
  const qkey={revenue_yoy:'sales_yoy_pct',opm:'op_margin_pct',ads:'ads_ratio_pct',
              fees:'selling_fee_ratio_pct',freight:'shipping_ratio_pct',
              cfo:'cash_conversion_pct'}[id];
  if(qkey)return fn.filter(x=>num(x[qkey])!=null).map(x=>({date:x.period,value:x[qkey]}));
  if(id==='per'||id==='pbr')return priceSnapshot(id);
  if(id==='roe')return safeArr(f.roe_ttm).map(x=>({date:x.period,value:x.roe_ttm_pct})).filter(x=>num(x.value)!=null);
  if(id==='inventory')return bn.filter(x=>num(x.reported_inventory_turnover)!=null).map(x=>({date:x.period,value:x.reported_inventory_turnover}));
  if(id==='fx')return safeArr(state.market?.fx).filter(x=>num(x.usdkrw)!=null).map(x=>({date:x.date,value:x.usdkrw}));
  if(id==='ulta'||id==='target')return retailHist.filter(x=>x.metric===(id==='ulta'?'catalog_items':'brand_catalog_items')).map(x=>({date:x.date,value:x.value}));
  if(id==='amazon')return safeArr(state.top100?.snapshots)
    .filter(x=>x.country==='US'&&x.coverage_complete&&num(x.medicube_confirmed_count)!=null)
    .map(x=>({date:x.date,value:x.medicube_confirmed_count}));
  if(id==='trends')return safeArr(d.trends).filter(x=>x.country==='US'&&String(x.term).toLowerCase()==='medicube'&&num(x.index)!=null)
    .map(x=>({date:x.date,value:x.index}));
  if(id==='insider')return insider.points;
  if(id==='reviews'){
   const rvs=safeArr(r.product_review_history).filter(x=>x.verified&&x.retailer==='target'&&num(x.reviews_count)!=null);
   return rvs.map(x=>({date:x.date,value:x.reviews_count}));
  }
  if(id==='retailer_statement')return [];
  if(id==='weekly')return amazonWeeks.map(x=>({date:x.week,value:x.count}));
  return [];
 }
 function sparkline(points){
   const rows=points.filter(x=>num(x.value)!=null).slice(-32);
   if(rows.length<2)return '<small class="thesis-trend-pending">시계열 누적 중 / 공개자료 미확인</small>';
   const vals=rows.map(x=>Number(x.value));
   let lo=Math.min(...vals),hi=Math.max(...vals);if(lo===hi){lo-=1;hi+=1}
   const coords=vals.map((v,i)=>[
      (3+i*104/(vals.length-1)).toFixed(1),
      (23-20*(v-lo)/(hi-lo)).toFixed(1)
   ]);
   const path=coords.map((p,i)=>(i?'L':'M')+p[0]+','+p[1]).join(' ');
   const diff=vals[vals.length-1]-vals[0];
   const pct=vals[0]?100*diff/Math.abs(vals[0]):null;
   const desc='최근 '+rows.length+'개 관측 · '+rows[0].date+' ~ '+rows[rows.length-1].date+
      ' · 변화 '+(pct==null?'절대 '+fmt(diff,1):fmt(pct,1)+'%');
   return '<svg viewBox="0 0 110 27" role="img" aria-label="'+escapeHtml(desc)+
     '" class="thesis-sparkline"><path d="'+path+
     '" fill="none" stroke="'+(diff>=0?'#26756b':'#bb5b63')+
     '" stroke-width="1.7" stroke-linecap="round" /></svg>'+
     '<small class="thesis-trend-metadata">'+escapeHtml(desc)+'</small>';
 }
 const root=$('thesis-blocks');
 if(root){
  const theses=safeArr(state.aprTheses?.theses);
  root.innerHTML=theses.map(group=>{
   const subtitle=group.id==='margin'?'수익성 악화 신호는 광고비·수수료·현금흐름과 함께 확인':
      group.id==='us'?'실제 재주문과 온라인 리뷰를 구분해서 점검':'과거 프리미엄과 이익 성장의 속도 차이를 확인';
   return '<article class="thesis-card"><div class="thesis-head"><div><small>'+escapeHtml(group.horizon||'')+
     '</small><h3>'+escapeHtml(group.title||'')+'</h3><p>'+escapeHtml(group.question||'')+
     '</p></div></div><p class="thesis-status">'+escapeHtml(subtitle)+'</p>'+
     '<div class="thesis-grid">'+safeArr(group.conditions).map(x=>
       '<div class="thesis-line"><strong>'+escapeHtml(x.label||'')+'</strong>'+
       '<span>'+escapeHtml(map[x.id]||'공식 공개자료 미확인')+'</span>'+
       sparkline(observations(x.id))+
       '<small>'+escapeHtml(x.source||'')+'</small></div>'
     ).join('')+'</div></article>';
  }).join('')||'<p class="subtle">지표를 불러오지 못했습니다.</p>';
 }
 const own=state.dartOwnership||{},el=$('dart-ownership-status'),body=$('dart-ownership-rows');
 if(el)el.textContent=own.status||'OpenDART API 조회 전 · 공개 공시 확보시 갱신';
 if(body){
  const filings=safeArr(own.filings);
  body.innerHTML=filings.slice(0,35).map(x=>'<tr>'+
    '<td>'+escapeHtml(x.date||'')+'</td><td>'+escapeHtml(x.reporter||'')+'</td>'+
    '<td>'+escapeHtml(x.type_label||x.type||'')+'</td><td>'+
    (num(x.ownership_pct)!=null?fmt(x.ownership_pct,2)+'%':'미표시')+'</td><td>'+
    (num(x.ownership_pct_change)!=null?(x.ownership_pct_change>0?'+':'')+fmt(x.ownership_pct_change,2)+'%p':'미확인')+'</td>'+
    '<td><a href="'+(x.source_url?.startsWith('https://dart.fss.or.kr/dsaf001/main.do?rcpNo=')?x.source_url:'#')+
    '" target="_blank" rel="noopener noreferrer">공시</a></td></tr>').join('')||
    '<tr><td colspan="6">OpenDART에서 검증된 에이피알 지분변동 기록이 아직 없습니다.</td></tr>';
 }

 const cap=state.dartCapital||{};
 const capStatus=$('dart-capital-status');
 if(capStatus)capStatus.textContent=cap.status||'OpenDART 배당·자기주식 공시 확인 전 · 기존 재무 기록 유지';
 const capRecords=safeArr(cap.observations).slice().sort((a,b)=>
   String(b.period||'').localeCompare(String(a.period||'')));
 const treasury=capRecords.filter(x=>x.type==='treasury_total'&&num(x.value)!=null);
 const byPeriod={};
 for(const item of treasury){
   if(!byPeriod[item.period])byPeriod[item.period]=[];
   byPeriod[item.period].push(item);
 }
 const periods=Object.keys(byPeriod).sort();
 const treasurySeries=periods.map(p=>{
   const items=byPeriod[p];
   // Different reported totals must not be arbitrarily combined.
   const unique=[...new Set(items.map(x=>Number(x.value)))];
   return unique.length===1?unique[0]:null;
 });
 chart('chart-dart-treasury',periods,[{
   label:'공시상 보통주 자기주식 기말 수량 (주)',
   values:treasurySeries,color:C.teal
 }],{decimals:0,legend:true});
 const capitalBody=$('dart-capital-rows');
 if(capitalBody){
  const rows=capRecords.filter(x=>x.type==='treasury_total'||
      (x.type==='dividend'&&/배당|주당|현금/i.test(x.metric||''))).slice(0,45);
  capitalBody.innerHTML=rows.length?rows.map(x=>{
    const valid=typeof x.source_url==='string'&&
      /^https:\/\/dart\.fss\.or\.kr\/dsaf001\/main\.do\?rcpNo=\d{14}$/.test(x.source_url);
    const type=x.type==='treasury_total'?'자기주식 기말 수량':x.metric;
    const stock=x.stock_type||'주식 종류 미확인';
    return '<tr><td>'+escapeHtml(x.period||'')+'</td>'+
     '<td>'+escapeHtml(type||'')+'</td>'+
     '<td>'+escapeHtml(stock)+'</td>'+
     '<td>'+fmt(x.value,0)+(x.type==='treasury_total'?'주':' (공시 단위)')+'</td>'+
     '<td>'+(valid?'<a href="'+x.source_url+
         '" target="_blank" rel="noopener noreferrer">원문</a>':'확인 전')+'</td></tr>';
  }).join(''):
  '<tr><td colspan="5">검증된 배당·자기주식 공시 자료가 아직 없습니다.</td></tr>';
 }

}

global.APR_RESEARCH={renderTrends,renderFinancials,renderTheses,renderRetail,ownershipSeries};
})(window);
