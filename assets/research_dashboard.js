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
 return last(list);
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
   label:name+' '+mult+'배',
   values:arr.map(v=>num(v)>0?Math.round(v*mult):null),
   color:colors[i%colors.length],width:1
  }));
  chart(id,labels,series,{decimals:0,legend:true,xticks:5});
 }
 bands(eps,'eps_won',multiplesPER,'chart-fin-per','PER');
 bands(book,'bps_won',multiplesPBR,'chart-fin-pbr','PBR');
 const note=$('fin-valuation-note');
 if(note){
  const missingJune=history.length&&history[0].date>'2025-06-09';
  note.textContent='PER 밴드는 단순 TTM EPS·PBR 밴드는 당시 공개 BPS로 산출한 참고가격이며 목표주가가 아닙니다. '+
    '미래에 발표된 손익·주식수를 과거 날짜에 소급하지 않습니다. '+
    '달러 시세는 당일(또는 확인 가능한 가장 가까운 직전일) 중앙은행 참조 USD/KRW 적용. '+
    (missingJune?'2025년 6월 초기 일봉은 아직 미수집되어 자료 확보일 이후만 표시합니다. ':'')+
    '실적/지배지분/지분율은 자료시차와 IFRS 1118 비교재표시 차이가 있을 수 있습니다.';
 }
}

function renderTheses(ctx){
 const {state,$,chart,escapeHtml,fmt,C}=ctx;
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
 chart('chart-off-amazon',aw.map(x=>x.week),[
  {label:'제3자 Amazon US Beauty Top100 메디큐브 종수',values:aw.map(x=>x.count),color:C.purple}
 ],{decimals:0,legend:true});
 const el=$('off-status');
 if(el)el.innerHTML=metrics.map(x=>{
   const stale=x.retailer==='target'&&x.metric==='zero_pore_pad_bought_lower';
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

 const qq=safeArr(f.quarterly),latestQ=last(qq),priorQ=qq.length>1?qq[qq.length-2]:null;
 const latestB=last(safeArr(f.balance)),roe=last(safeArr(f.roe_ttm));
 const stock=last(safeArr(state.market?.series));
 const eps=stock?latestRelease(safeArr(f.valuation?.eps_events),stock.date,'eps_won'):null;
 const bps=stock?latestRelease(safeArr(f.valuation?.book_events),stock.date,'bps_won'):null;
 const per=stock&&eps?stock.close_krw/eps.eps_won:null,pbr=stock&&bps?stock.close_krw/bps.bps_won:null;
 const usTop=last(safeArr(state.top100?.snapshots).filter(x=>x.country==='US').sort((a,b)=>a.date.localeCompare(b.date)));
 const yoy=latestQ?.sales_yoy_pct;
 const map={
  per:per?fmt(per,1)+'배 (TTM 참고)':'EPS 기준 미확인',
  pbr:pbr?fmt(pbr,1)+'배 (최근 공시 BPS)':'BPS 기준 미확인',
  revenue_yoy:num(yoy)!=null?(yoy>=0?'+':'')+fmt(yoy,1)+'% · '+latestQ.period:'전년 동기 비교 미확인',
  roe:roe?fmt(roe.roe_ttm_pct,1)+'% · '+roe.period:'비교 자본 자료 미확인',
  consensus:'검증된 증권사 컨센서스 시계열 미수집',
  insider:'DART 지분 변동 정량자료 미수집',
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
  weekly:aw.length?fmt(aw[0].count)+' → '+fmt(last(aw).count)+'개 ('+aw[0].week+'~'+last(aw).week+')':'주간 제3자 지표 미수집',
  trends:safeArr(t.alerts).some(x=>x.country==='US')?safeArr(t.alerts).filter(x=>x.country==='US').map(x=>x.keyword+' '+x.direction).join(', '):'미국에서 기준을 충족한 유의미 변화 미감지 또는 자료 부족',
  reorders:'공식 POS·재주문 수량 미공개'
 };
 const root=$('thesis-blocks');
 if(root){
  const theses=safeArr(state.aprTheses?.theses);
  root.innerHTML=theses.map(group=>{
   let subtitle='';
   if(group.id==='margin'&&latestQ&&priorQ&&num(latestQ.op_margin_pct)!=null&&num(priorQ.op_margin_pct)!=null&&latestQ.op_margin_pct-priorQ.op_margin_pct<=-3){
      subtitle='영업이익률이 전분기 대비 3%p 이상 낮아져 점검 필요';
   } else if(group.id==='us')subtitle='초도 입점과 실제 판매·재주문을 별도로 확인';
   else subtitle='단일 지표만으로 저평가·고평가를 단정하지 않음';
   return '<article class="thesis-card"><div class="thesis-head"><div><small>'+escapeHtml(group.horizon||'')+'</small><h3>'+escapeHtml(group.title||'')+'</h3><p>'+escapeHtml(group.question||'')+'</p></div></div>'+
    '<p class="thesis-status">'+escapeHtml(subtitle)+'</p>'+
    '<div class="thesis-grid">'+safeArr(group.conditions).map(x=>
     '<div class="thesis-line"><strong>'+escapeHtml(x.label||'')+'</strong>'+
     '<span>'+escapeHtml(map[x.id]||'확인 필요')+'</span>'+
     '<small>'+escapeHtml(x.source||'')+'</small></div>'
    ).join('')+'</div></article>';
  }).join('')||'<p class="subtle">투자 가설 확인 지표를 불러오지 못했습니다.</p>';
 }
}

global.APR_RESEARCH={renderTrends,renderFinancials,renderTheses};
})(window);
