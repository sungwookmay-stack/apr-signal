/* APR SIGNAL Research · financial statements, valuation, offline proxies.
   All public values are historical and source-labeled, not buy/sell advice. */
(()=>{'use strict';
const ok=n=>typeof n==='number'&&Number.isFinite(n);
const num=(n,d=1)=>ok(n)?n.toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d}):'—';
const percent=n=>ok(n)?num(n,1)+'%':'—';
const won=n=>ok(n)?'₩'+num(n,0):'—';
const amount=n=>ok(n)?num(n,1)+'억':'—';
const sorted=(a,k)=>Array.isArray(a)?a.slice().sort((x,y)=>String(x[k]??'').localeCompare(String(y[k]??''))):[];
const last=a=>a.length?a[a.length-1]:null;
const get=(arr,k,v)=>(arr||[]).find(x=>x[k]===v);
function eventAsOf(events,date){
 const valid=sorted(events,'available_from').filter(x=>x.available_from<=date);
 return last(valid);
}
function roeProxies(f){
 const ann=get(f.annual,'period','2025FY'),bs=f.balance||[];
 const fy=get(bs,'period','2025FY'),fy0=get(bs,'period','2024FY');
 const q2=get(bs,'period','2026Q2');
 const qs=f.quarterly||[];
 const p1=get(qs,'period','2025Q1'),p2=get(qs,'period','2025Q2'),t1=get(qs,'period','2026Q1'),t2=get(qs,'period','2026Q2');
 const r=[];
 if(ann&&fy&&fy0&&fy.equity+fy0.equity>0)r.push({period:'2025FY',value:2*100*ann.net_income/(fy.equity+fy0.equity)});
 if(ann&&fy&&q2&&p1&&p2&&t1&&t2&&fy.equity+q2.equity>0){
 const income=ann.net_income-p1.ni-p2.ni+t1.ni+t2.ni;
 r.push({period:'2026H1 TTM',value:2*100*income/(fy.equity+q2.equity)});
 }
 return r;
}
function renderMatrix(ctx){
 const {state,$,escapeHtml}=ctx,f=state.financials||{},kind=$('fin-table-kind')?.value||'income';
 const q=sorted(f.quarterly,'period'),bs=sorted(f.balance,'asof');
 let head=[],rows=[],notice='';
 const cell=x=>ok(x)?num(x,1):'—';
 if(kind==='expenses'){
 head=['분기','판관비','광고선전비','판매수수료','운반비','광고/매출','수수료/매출','운반/매출'];
 rows=q.map(x=>[x.period,cell(x.sga),cell(x.ads),cell(x.fees),cell(x.logistics),percent(x.ads_ratio_pct),percent(x.selling_fee_ratio_pct),percent(x.shipping_ratio_pct)]);
 notice='2025년 4Q는 연간 사업보고서−3Q 누계. 2026년 3Q 비용은 정식 공시가 없으면 공란 유지.';
 }else if(kind==='balance'){
 head=['기준','재고자산','총자산','매출채권','현금성자산','재고/자산','회전율','재고일수'];
 rows=bs.map(x=>[x.period,cell(x.inventory),cell(x.assets),cell(x.receivables),cell(x.cash),percent(x.inventory_assets_pct),ok(x.reported_inventory_turnover)?num(x.reported_inventory_turnover,1)+'회':'—',ok(x.inventory_days_company)?num(x.inventory_days_company,0)+'일':'—']);
 notice='매출원가/평균 재고에 기초한 공시 연환산 회전율. 재고일수(365÷회전율)는 참고치.';
 }else if(kind==='cashflow'){
 head=['분기','영업현금흐름','유형자산 취득','FCF 참고','순이익','현금전환율'];
 rows=q.map(x=>[x.period,cell(x.cfo),cell(x.capex),cell(x.fcf_proxy),cell(x.ni),percent(x.cash_conversion_pct)]);
 notice='FCF 참고=영업현금흐름−유형자산 취득. 무형자산 투자 등은 미반영.';
 }else if(kind==='returns'){
 head=['기간','ROE(%)','ROIC','정의'];
 rows=roeProxies(f).map(x=>[x.period,percent(x.value),'미산출','연결 총자본 기준 참고치']);
 notice='정확한 지배주주 ROE 및 ROIC는 이자부채·유효세율·투하자본·지배순이익 검증 전 미산출.';
 }else{
 head=['분기','매출액','영업이익','순이익','매출 YoY','영업이익률','순이익률','자료 상태'];
 rows=q.map(x=>[x.period,cell(x.sales),cell(x.op),cell(x.ni),percent(x.sales_yoy_pct),percent(x.op_margin_pct),percent(x.net_margin_pct),x.status||'']);
 notice='연결 기준·단위 억원. 2025년 4Q는 연간−3Q 누계로 계산. 2026년 3Q는 잠정.';
 }
 if($('fin-table-head'))$('fin-table-head').innerHTML='<tr>'+head.map(x=>'<th>'+escapeHtml(x)+'</th>').join('')+'</tr>';
 if($('fin-table-body'))$('fin-table-body').innerHTML=rows.map(row=>'<tr>'+row.map(x=>'<td>'+escapeHtml(x)+'</td>').join('')+'</tr>').join('');
 if($('fin-table-footnote'))$('fin-table-footnote').textContent=notice;
}
function valuationRows(state){
 const prices=sorted((state.market?.series||[]).filter(x=>x.date>='2025-06-01'&&ok(x.close_krw)),'date');
 const eps=state.financials?.valuation?.eps_events||[];
 const book=state.financials?.valuation?.book_events||[];
 return prices.map(x=>({...x,eps:eventAsOf(eps,x.date),book:eventAsOf(book,x.date)}));
}
function renderFinancials(ctx){
 const {state,$,chart,C,escapeHtml}=ctx,f=state.financials;
 if(!f||!Array.isArray(f.quarterly)||!f.quarterly.length){
 if($('fin-sources'))$('fin-sources').textContent='재무 자료 갱신 전. 확인되지 않은 금액은 표시하지 않습니다.';
 return;
 }
 const q=sorted(f.quarterly,'period'),b=sorted(f.balance,'asof'),lastQ=last(q),lastB=last(b);
 const txt=(id,x)=>{if($(id))$(id).textContent=x};
 txt('fin-revenue',amount(lastQ.sales));txt('fin-revenue-period',lastQ.period+' · '+lastQ.status);
 txt('fin-opm',percent(lastQ.op_margin_pct));txt('fin-opm-period',lastQ.period);
 txt('fin-inventory',amount(lastB.inventory));txt('fin-inventory-period',lastB.asof+' 기준');
 txt('fin-turnover',num(lastB.reported_inventory_turnover,1)+'회');txt('fin-turnover-period',lastB.asof+' 연환산');
 const labels=q.map(x=>x.period),bdates=b.map(x=>x.period);
 chart('chart-fin-sales',labels,[
  {label:'매출',values:q.map(x=>x.sales),color:C.navy},
  {label:'영업이익',values:q.map(x=>x.op),color:C.teal},
  {label:'순이익',values:q.map(x=>x.ni),color:C.orange}],{decimals:0,legend:true});
 chart('chart-fin-margins',labels,[
  {label:'영업이익률',values:q.map(x=>x.op_margin_pct),color:C.teal},
  {label:'순이익률',values:q.map(x=>x.net_margin_pct),color:C.purple},
  {label:'판관비율',values:q.map(x=>x.sga_ratio_pct),color:C.orange}],{decimals:1,legend:true,suffix:'%'});
 chart('chart-fin-inventory',bdates,[
  {label:'재고(억)',values:b.map(x=>x.inventory),color:C.navy},
  {label:'재고/총자산(%)',values:b.map(x=>x.inventory_assets_pct),color:C.orange,axis:'y1'}],{legend:true,y1:true,decimals:1});
 chart('chart-fin-expense',labels,[
  {label:'광고/매출',values:q.map(x=>x.ads_ratio_pct),color:C.navy},
  {label:'판매수수료/매출',values:q.map(x=>x.selling_fee_ratio_pct),color:C.teal},
  {label:'운반비/매출',values:q.map(x=>x.shipping_ratio_pct),color:C.purple}],{legend:true,decimals:1,suffix:'%'});
 chart('chart-fin-cfo',labels,[
  {label:'영업현금(억)',values:q.map(x=>x.cfo),color:C.teal},
  {label:'순이익(억)',values:q.map(x=>x.ni),color:C.orange}],{legend:true,decimals:0});
 const roes=roeProxies(f);
 chart('chart-fin-roe',roes.map(x=>x.period),[
  {label:'ROE 참고치(%)',values:roes.map(x=>Math.round(x.value*100)/100),color:C.navy}],{legend:true,decimals:1,suffix:'%'});
 renderMatrix(ctx);
 txt('fin-sources',f.accounting_note+' · '+(f.source_files||[]).join(' / '));
 const daily=valuationRows(state),dates=daily.map(x=>x.date);
 txt('fin-price-date',(daily[0]?.date||'—')+' ~ '+(last(daily)?.date||'—')+' · 실측 일봉');
 chart('chart-fin-krw',dates,[{label:'APR 종가(원)',values:daily.map(x=>x.close_krw),color:C.navy}],{decimals:0});
 chart('chart-fin-usd',dates,[{label:'APR 주가(달러)',values:daily.map(x=>ok(x.close_usd)?x.close_usd:null),color:C.teal}],{decimals:2});
 const per=(f.valuation?.per_multiples||[15,25,35,45,55]),pbr=(f.valuation?.pbr_multiples||[5,10,15,20,25]);
 const colors=[C.grey,C.purple,C.orange,C.teal,C.navy];
 chart('chart-fin-per',dates,[
  {label:'실제 종가',values:daily.map(x=>x.close_krw),color:'#111111',width:2.4},
  ...per.map((v,i)=>({label:v+'배',values:daily.map(x=>x.eps&&ok(x.eps.eps_won)?Math.round(x.eps.eps_won*v):null),color:colors[i],dash:[4,3]}))
 ],{legend:true,decimals:0,smooth:0});
 chart('chart-fin-pbr',dates,[
  {label:'실제 종가',values:daily.map(x=>x.close_krw),color:'#111111',width:2.4},
  ...pbr.map((v,i)=>({label:v+'배',values:daily.map(x=>x.book&&ok(x.book.bps_won)?Math.round(x.book.bps_won*v):null),color:colors[i],dash:[4,3]}))
 ],{legend:true,decimals:0,smooth:0});
 const pl=last(daily),eps=pl?.eps,book=pl?.book;
 txt('fin-valuation-note','최종일 '+(pl?.date||'—')+' · TTM EPS '+(eps?num(eps.eps_won,0)+'원':'미확인')+' ('+(eps?.eps_quality||'공시 전')+')'+
   ' · BPS '+(book?num(book.bps_won,0)+'원':'미확인')+
   ' · 현재 PER '+(eps?.eps_won>0?num(pl.close_krw/eps.eps_won,1)+'배':'—')+
   ' · PBR '+(book?.bps_won>0?num(pl.close_krw/book.bps_won,1)+'배':'—')+
   '. 주당이익은 TTM 단순 추정치(발행주식수 기준)이며 미래 추정 EPS/공식 컨센서스가 아닙니다.');
}
function renderTrends(ctx){
 const {state,$,escapeHtml}=ctx;
 const r=state.trendSignals||{},alerts=Array.isArray(r.alerts)?r.alerts:[],target=$('trend-alerts');
 if($('trend-alert-count'))$('trend-alert-count').textContent=alerts.length+'개 유의 변화';
 if(!target)return;
 target.innerHTML=alerts.length?alerts.slice(0,12).map(x=>{
 const up=x.direction.includes('상승');
 return '<article class="signal-shift '+(up?'shift-up':'shift-down')+'">'+
  '<div class="signal-shift-top"><strong>'+escapeHtml(x.country_name||x.country)+'</strong>'+
  '<span>'+escapeHtml(x.direction)+'</span></div>'+
  '<h4>'+escapeHtml(x.keyword)+'</h4>'+
  '<div class="signal-shift-fig">'+(x.change_pct>0?'+':'')+num(x.change_pct,1)+'%'+
  ' <small>기준 대비 '+(x.delta_index>0?'+':'')+num(x.delta_index,1)+'p</small></div>'+
  '<p>최근 평균 '+num(x.recent_avg,1)+' / 이전 '+num(x.baseline_avg,1)+
  ' · '+escapeHtml(x.asof)+' · '+escapeHtml(x.granularity)+'</p>'+
  '</article>';
 }).join(''):'<p class="subtle">현재 기준을 모두 충족한 검색 급변 신호가 없습니다. 수집자료가 부족하거나 비교 기준이 다르면 신호를 생성하지 않습니다.</p>';
 if($('trend-note'))$('trend-note').textContent=(r.method||'같은 국가·키워드의 평균 변화만 비교')+
 ' · Google Trends는 국가 간 절대량 비교 불가, 매출·판매량 아님. '+(r.evaluated_pairs||0)+'개 시계열 검토.';
}
function renderTheses(ctx){
 const {state,$,chart,C,escapeHtml}=ctx,f=state.financials||{},
 ref=state.reference||{},theses=state.aprTheses||{},lastFin=last(sorted(f.quarterly,'period'));
 const latestRetail=ref.retail||[],history=sorted(ref.retail_history,'date'),ulta=metric(latestRetail,'catalog_items'),
 online=metric(latestRetail,'online_only_items'),target=metric(latestRetail,'brand_catalog_items');
 const txt=(id,value)=>{const x=$(id);if(x)x.textContent=value;};
 txt('off-ulta-total',ulta?num(ulta.value,0)+'개':'—');
 txt('off-ulta-date',ulta?.date||'검증 자료 없음');
 txt('off-ulta-online',online?num(online.value,0)+'개':'—');
 txt('off-ulta-eligible',ulta&&online&&ulta.date===online.date&&ulta.value>=online.value?num(ulta.value-online.value,0)+'개':'—');
 txt('off-target-total',target?num(target.value,0)+'개':'미수집');
 txt('off-target-date',target?.date||'Target 브랜드 SKU 공식 확인 전');
 const kinds=['catalog_items','online_only_items','brand_catalog_items','brand_zero_pore_bought_lower'];
 const dates=[...new Set(history.filter(x=>kinds.includes(x.metric)).map(x=>x.date))].sort();
 chart('chart-off-retail',dates,[
  {label:'Ulta 전체',color:C.navy,values:dates.map(d=>get(history.filter(x=>x.date===d),'metric','catalog_items')?.value??null)},
  {label:'Ulta 온라인 전용',color:C.orange,values:dates.map(d=>get(history.filter(x=>x.date===d),'metric','online_only_items')?.value??null)},
  {label:'Target 브랜드 전체',color:C.teal,values:dates.map(d=>get(history.filter(x=>x.date===d),'metric','brand_catalog_items')?.value??null)}],{legend:true,decimals:0});
 const amazon=sorted(ref.amazon_weekly,'week');
 chart('chart-off-amazon',amazon.map(x=>x.week),[
  {label:'미국 Amazon Top100: 제3자 주간 진입종',color:C.purple,values:amazon.map(x=>x.count)}],{legend:true,decimals:0});
 const status=$('off-status');
 if(status)status.innerHTML=latestRetail.map(x=>'<div class="retail-signal"><strong>'+escapeHtml((x.retailer||'').toUpperCase()+' · '+(x.label||x.metric))+'</strong>'+
  '<span>'+escapeHtml(x.display||num(x.value,0))+' · '+escapeHtml(x.date||'날짜 미확인')+'</span>'+
  '<small>원본 기준: '+escapeHtml(x.scope||'')+' · '+escapeHtml(x.note||'')+'</small>'+
  (x.source_url?'<a href="'+ctx.validLink(x.source_url)+'" target="_blank" rel="noopener noreferrer">공식 출처 보기 ↗</a>':'')+
  '</div>').join('');
 const targetFailure=(ref.collection?.failures||[]).some(x=>String(x).startsWith('target:'));
 if($('off-target-warning'))$('off-target-warning').textContent=targetFailure?
  'Target 자동 수집 실패: 저장된 이전 관측은 보존하며 새로운 브랜드 SKU/구매 배지를 임의로 만들지 않습니다. 카테고리 9개와 브랜드 전체 상품 수를 구분합니다.':
  'Target 브랜드 상품 수와 일부 카테고리 상품 수는 다른 지표입니다. 구매 배지는 실제 오프라인 POS가 아닙니다.';
 const items=theses.theses||[],root=$('thesis-blocks');if(!root)return;
 const values={
  per:()=>{const p=last(valuationRows(state));return p?.eps?.eps_won>0?num(p.close_krw/p.eps.eps_won,1)+'배':'미수집'},
  pbr:()=>{const p=last(valuationRows(state));return p?.book?.bps_won>0?num(p.close_krw/p.book.bps_won,1)+'배':'미수집'},
  revenue_yoy:()=>percent(lastFin?.sales_yoy_pct),opm:()=>percent(lastFin?.op_margin_pct),
  ads:()=>percent(lastFin?.ads_ratio_pct),fees:()=>percent(lastFin?.selling_fee_ratio_pct),
  freight:()=>percent(lastFin?.shipping_ratio_pct),
  inventory:()=>{const b=last(sorted(f.balance,'asof'));return b&&ok(b.reported_inventory_turnover)?num(b.reported_inventory_turnover,1)+'회':'미수집'},
  cfo:()=>percent(lastFin?.cash_conversion_pct),
  fx:()=>{const p=last(sorted(state.market?.fx,'date'));return ok(p?.usdkrw)?num(p.usdkrw,1)+'원':'미수집'},
  costco:()=> '약 400점(2026.10 보도)',ulta:()=>ulta?num(ulta.value,0)+'개':'미수집',
  target:()=>target?num(target.value,0)+'개':'미수집',
  amazon:()=>{const a=sorted((state.top100?.snapshots||[]).filter(x=>x.country==='US'),'date');const r=last(a);return r?(r.medicube_confirmed_count>0?'최소 '+r.medicube_confirmed_count+'종':'진입 여부 미확인'):'미수집'},
  weekly:()=>{const a=last(amazon);return a?num(a.count,0)+'종 ('+a.week+')':'미수집'},
  trends:()=>{const a=(state.trendSignals?.alerts||[]).filter(x=>x.country==='US');return a.length?a[0].keyword+' '+(a[0].change_pct>0?'+':'')+num(a[0].change_pct,0)+'%':'유의한 변화 없음'}
 };
 root.innerHTML=items.map(x=>'<article class="thesis-card">'+
  '<div class="thesis-head"><span>THESIS · '+escapeHtml(x.horizon||'')+'</span><h3>'+escapeHtml(x.title)+'</h3><p>'+escapeHtml(x.question||'')+'</p></div>'+
  '<div class="thesis-indicators">'+(x.conditions||[]).map(c=>'<div class="thesis-indicator">'+
  '<div><strong>'+escapeHtml(c.label)+'</strong><small>'+escapeHtml(c.source||'')+'</small></div>'+
  '<b>'+escapeHtml(values[c.id]?values[c.id]():'확인 필요')+'</b></div>').join('')+
  '</div><p class="thesis-foot">'+escapeHtml(x.description||'')+'</p></article>').join('');
}
window.APR_RESEARCH={renderFinancials,renderTheses,renderTrends,valuationRows,roeProxies};
})();
