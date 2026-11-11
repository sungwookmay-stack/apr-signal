/* APR SIGNAL • Free, static, sourced market monitor. No trading order function. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const fmt=(n,d=0)=>n==null||!Number.isFinite(Number(n))?'—':Number(n).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=(a,b)=>a!=null&&b!=null&&Number(b)!==0?(a/b-1)*100:null;
const signed=(n,d=1)=>n==null?'—':(n>0?'+':'')+fmt(n,d)+'%';
const state={market:null,tech:null,kbty:null,news:null,demand:null,status:null,financials:null,trendSignals:null,aprTheses:null,period:'all',country:'US',brand:'medicube',product:'all',nav:'overview',charts:{},top50:null,reference:null,kitaRates:null,flows:null,flowReference:null,dartOwnership:null,dartFinancials:null,dartCapital:null,techView:'ma',techPeriod:'120'};
const C={navy:'#293841',teal:'#26756b',orange:'#c19561',purple:'#786a9d',grey:'#a1a9b0',red:'#bb5b63'};
const missing='실측 데이터 없음 · 확인된 값만 표시합니다.';
const minimalMarkets=[{code:'US',name:'미국',region:'북미',amazon:'amazon.com'},{code:'GB',name:'영국',region:'유럽',amazon:'amazon.co.uk'},{code:'DE',name:'독일',region:'유럽',amazon:'amazon.de'},{code:'FR',name:'프랑스',region:'유럽',amazon:'amazon.fr'},{code:'IT',name:'이탈리아',region:'유럽',amazon:'amazon.it'},{code:'ES',name:'스페인',region:'유럽',amazon:'amazon.es'},{code:'CA',name:'캐나다',region:'북미',amazon:'amazon.ca'},{code:'JP',name:'일본',region:'아시아',amazon:'amazon.co.jp'},{code:'AE',name:'아랍에미리트',region:'중동',amazon:'amazon.ae'},{code:'SA',name:'사우디아라비아',region:'중동',amazon:'amazon.sa'},{code:'EG',name:'이집트',region:'중동',amazon:'amazon.eg'},{code:'QA',name:'카타르',region:'중동',amazon:null},{code:'KW',name:'쿠웨이트',region:'중동',amazon:null},{code:'BR',name:'브라질',region:'남미',amazon:'amazon.com.br',amazon_beauty_slug:'beauty'},{code:'AR',name:'아르헨티나',region:'남미',amazon:null},{code:'CL',name:'칠레',region:'남미',amazon:null}];
function countryMarkets(){
 const actual=state.demand?.countries?.length?state.demand.countries:minimalMarkets;
 const missingMarkets=minimalMarkets.filter(x=>!actual.some(y=>y.code===x.code));
 return actual.concat(missingMarkets).map(x=>['BR','AR','CL'].includes(x.code)?{...x,region:'남미'}:x);
}
function rankSnapshots(){return (state.top50?.snapshots||[]).map(s=>{const b=s.brands?.[state.brand]||(state.brand==='medicube'?s:{items:[],exited:[],verified_count:0,candidate_count:0});return {...s,...b,date:s.observed_at_utc,medicube_listings:b.items||[]};});}
function set(id,val){const e=$(id);if(e)e.textContent=val;}
function safeText(s){return String(s??'');}
function escapeHtml(s){return safeText(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function validLink(url){try{let u=new URL(url);return ['https:','http:'].includes(u.protocol)?u.href:'#'}catch{return '#'}}
async function getJSON(name){try{const r=await fetch('./data/'+name+'.json?v='+Date.now(),{cache:'no-store'});if(r.ok)return await r.json()}catch{}return window.APR_BOOTSTRAP?.[name]??null}
function today(){return new Date().toISOString().slice(0,10)}
function showPage(hash){const id=(hash||location.hash||'#overview').replace('#','');state.nav=['overview','technical','flows','financials','demand','theses','kbty','business','logistics','sensitivity'].includes(id)?id:'overview';document.querySelectorAll('[data-page]').forEach(x=>x.classList.toggle('active',x.dataset.page===state.nav));document.querySelectorAll('[data-nav]').forEach(x=>x.classList.toggle('active',x.dataset.nav===state.nav));document.querySelectorAll('[data-mnav]').forEach(x=>x.classList.toggle('active',x.dataset.mnav===state.nav));if(state.nav==='technical')renderTechnical();if(state.nav==='flows'&&window.APR_FLOWS)window.APR_FLOWS.render(researchContext());if(state.nav==='financials'&&window.APR_RESEARCH)window.APR_RESEARCH.renderFinancials(researchContext());if(state.nav==='theses'&&window.APR_RESEARCH)window.APR_RESEARCH.renderTheses(researchContext());if(state.nav==='demand'){renderDemand();if(window.APR_RESEARCH)window.APR_RESEARCH.renderRetail(researchContext());}if(state.nav==='kbty')renderEtf();if(state.nav==='business')renderNews();if(state.nav==='logistics')renderLogistics();if(state.nav==='sensitivity'&&window.APR_SENSITIVITY)window.APR_SENSITIVITY.render(researchContext());if(state.nav==='overview')renderOverview();window.scrollTo({top:0,behavior:'instant'});}
function researchContext(){return {state,$,chart,escapeHtml,fmt,C,validLink};}
function marketRows(){return (state.market?.series||[]).filter(x=>x.date>='2025-06-01'&&x.close_krw).sort((a,b)=>a.date.localeCompare(b.date));}
function dateLimit(rows){const n=Number(state.period);return Number.isFinite(n)&&n>0?rows.filter(x=>x.date>=new Date(Date.now()-n*86400000).toISOString().slice(0,10)):rows;}
function chart(id,labels,series,extra={}){
 const el=$(id);if(!el)return;
 const prev=state.charts[id];if(prev){prev.destroy();delete state.charts[id]}
 if(typeof Chart==='undefined'){const alt=$(id.replace('chart-','fallback-'));if(alt)alt.hidden=false;el.style.display='none';return}
 el.style.display='block';
 const datasets=series.map((x,i)=>({
    label:x.label||'—',data:x.values||[],borderColor:x.color||Object.values(C)[i%5],
    backgroundColor:x.background||'transparent',borderWidth:x.width??2,
    pointRadius:labels.length<=1?5:0,pointHoverRadius:5,tension:extra.smooth??0.15,
    spanGaps:false,fill:x.fill??false,yAxisID:x.axis||'y',borderDash:x.dash||[],
    ...(x.type?{type:x.type}:{}),...(extra.datasetOverrides||{})
 }));
 const scales={
   x:{grid:{display:false},ticks:{color:'#9babb7',maxTicksLimit:extra.xticks||6,font:{size:10},maxRotation:0}},
   y:{grid:{color:'#edf1f3'},ticks:{color:'#9babb7',font:{size:10},callback:v=>extra.yformat==='k'?Math.round(v/1000)+'K':v},...(extra.yOptions||{})}
 };
 if(extra.y1)scales.y1={type:'linear',display:true,position:'right',grid:{drawOnChartArea:false},ticks:{color:'#9babb7',font:{size:10}}};
 state.charts[id]=new Chart(el.getContext('2d'),{
   type:extra.type||'line',data:{labels,datasets},
   options:{responsive:true,maintainAspectRatio:false,animation:false,
    interaction:{mode:'index',intersect:false},
    plugins:{legend:{display:extra.legend??false,position:'bottom',labels:{boxWidth:12,font:{family:'sans-serif',size:10},color:'#718697'}},
      tooltip:{callbacks:{label:ctx=>`${ctx.dataset.label}: ${fmt(ctx.parsed.y,extra.decimals||0)}${extra.suffix||''}`}}},
    scales}
 });
}
function showMarketEmpty(){set('price-coverage','시세 미수집 / 데이터 수집 상태를 확인하세요.');}
function renderOverview(){
 const all=marketRows();if(!all.length){showMarketEmpty();return}
 const x=all[all.length-1],first=all[0],validUSD=all.filter(z=>z.close_usd!=null),fFirst=validUSD[0],fLast=validUSD[validUSD.length-1];
 set('m-krw','₩'+fmt(x.close_krw));set('m-usd',x.close_usd!=null?'$'+fmt(x.close_usd,2):'—');
 set('m-fxusd',x.usdkrw!=null?fmt(x.usdkrw,1):'—');set('m-fxeur',x.eurkrw!=null?fmt(x.eurkrw,1):'—');
 set('m-krw-note',signed(pct(x.close_krw,first.close_krw))+' · 보유된 첫 데이터 대비');
 set('m-fxusd-note','마지막 시세 '+(x.fx_usd_date||'미확인'));
 let rows=dateLimit(all);let b=rows[0],bu=rows.find(z=>z.close_usd!=null);
 if(rows.length){chart('chart-return',rows.map(z=>z.date.slice(5)),[
   {label:'KRW',values:rows.map(z=>100*z.close_krw/b.close_krw),color:C.navy},
   {label:'USD',values:rows.map(z=>bu&&z.close_usd!=null?100*z.close_usd/bu.close_usd:null),color:C.teal}
 ],{decimals:1});
 chart('chart-price',rows.map(z=>z.date.slice(5)),[
   {label:'KRW',values:rows.map(z=>z.close_krw),color:C.navy,axis:'y'},
   {label:'USD',values:rows.map(z=>z.close_usd),color:C.teal,axis:'y1'}],{y1:true,yformat:'k'});
 }
 let fxrows=(state.market.fx||[]).filter(z=>z.date>=rows[0]?.date&&z.date<=rows[rows.length-1]?.date);
 chart('chart-fx',fxrows.map(z=>z.date.slice(5)),[
   {label:'USD/KRW',values:fxrows.map(z=>z.usdkrw),color:C.orange},
   {label:'EUR/KRW',values:fxrows.map(z=>z.eurkrw),color:C.purple}],{decimals:1});
 const firstDate=all[0].date,lastDate=x.date;
 set('price-coverage',firstDate+' — '+lastDate+' · '+all.length+'거래일 기록');
 const buckets={};for(const z of all){let mon=z.date.slice(0,7);(buckets[mon]??={prices:[],fxusd:[],fxeur:[]}).prices.push(z)}
 for(const z of state.market.fx||[]){let mon=z.date.slice(0,7);if(!buckets[mon])buckets[mon]={prices:[],fxusd:[],fxeur:[]};if(z.usdkrw)buckets[mon].fxusd.push(z.usdkrw);if(z.eurkrw)buckets[mon].fxeur.push(z.eurkrw)}
 $('monthly-body').innerHTML=Object.keys(buckets).sort().reverse().map(mon=>{const o=buckets[mon];const p=o.prices.at(-1);const avg=a=>a.length?a.reduce((s,v)=>s+v,0)/a.length:null;
 return `<tr><td>${escapeHtml(mon)}${p&&mon===lastDate.slice(0,7)?' (진행 중 · '+escapeHtml(p.date.slice(5))+')':''}</td><td>${p?'₩'+fmt(p.close_krw):'—'}</td><td>${p&&p.close_usd!=null?'$'+fmt(p.close_usd,2):'—'}</td><td>${fmt(avg(o.fxusd),1)}</td><td>${fmt(avg(o.fxeur),1)}</td></tr>`}).join('');
}
function renderBottomAnalysis(b){
 set('bottom-date',b?.date?'확인 일봉 '+b.date:'자료 검증 전');
 set('bottom-stage',b?.stage||'자료 부족 · 판단 유보');
 set('bottom-score',b?.score!=null?b.score+' / '+(b.max_score||10):'—');
 set('bottom-low',b?.reference?.recent_20d_low!=null?'₩'+fmt(b.reference.recent_20d_low):'—');
 set('bottom-low-date',b?.reference?.recent_20d_low_date||
     '최근 20거래일 저가 확인 전');
 set('bottom-ma20',b?.reference?.ma20!=null?'₩'+fmt(b.reference.ma20):'—');
 const stage=(b?.kind||'unknown');
 const guidance={
    confirmation:'반등 흐름의 1차 확인 조건을 충족했으나 이후 저점 재시험 가능',
    building:'다이버전스·재시험과 모멘텀이 동반돼 형성 가능성 상승',
    early:'투매 후 매도압력이 둔화될 수 있으나 저점 확정 전',
    risk:'저점 재이탈·하락 지속 가능성 점검 필요',
    unknown:'바닥이 확인됐다는 근거 부족'
 }[stage]||'추가 거래일이 필요';
 set('bottom-guidance',guidance);
 if(!b?.data_ready){
    set('bottom-washout','OHLCV·RSI·MACD 자료 검증 전: 저점 판단 보류');
    set('bottom-conditions','자료가 충분한 실제 일봉이 확보된 후 표시합니다.');
    const checks=$('bottom-checks');if(checks)checks.innerHTML='';
    return;
 }
 const w=b.washout,low=b.reference||{};
 set('bottom-washout',w?
   '최근 투매 관측: '+w.date+' · 이전 20일 평균 대비 거래량 '+
    fmt(w.volume_multiple,1)+'배 · 최근 60일 고점 대비 당일 -'+
    fmt(Math.abs(w.drawdown_from_60d_top_pct),1)+'%':
   '최근 20거래일 기준에 맞는 투매·거래량 급증 신호는 미확인');
 const checks=$('bottom-checks');if(checks){
   checks.innerHTML=(b.checks||[]).map(x=>
      '<div class="check"><span class="check-icon '+(x.passed?'positive':'caution')+'">'+
      (x.passed?'✓':'·')+'</span><div><b>'+escapeHtml(x.name)+
      ' <small>+'+(x.passed?x.points:0)+' / '+x.max_points+'</small></b><p>'+
      escapeHtml(x.detail)+'</p></div></div>'
   ).join('');
 }
 const pivot=b.latest_confirmed_swing_low;
 set('bottom-conditions','관찰 기준: 최근 20일 저점 '+
   (low.recent_20d_low!=null?'₩'+fmt(low.recent_20d_low):'미확인')+
   ' · 5일선 '+(low.ma5!=null?'₩'+fmt(low.ma5):'—')+
   ' · 직전 10거래일 최고종가 '+(low.prior_10d_high_close!=null?'₩'+fmt(low.prior_10d_high_close):'—')+
   ' · 마지막 확인된 스윙 저점 '+(pivot?pivot.date+' ₩'+fmt(pivot.low)+
      ' (확인일 '+pivot.confirmed_on+')':'없음')+
   ' · 3거래일 이후에만 스윙 저점 확정. 이는 지지·손절 보장선이 아닙니다.');
}
function renderTechnical(){const d=state.technical,last=d?.last;
 renderBottomAnalysis(d?.bottom);
 if(!last||!last.date){set('t-decision','분석 자료 미확보');set('t-add','보류');return}
 set('t-decision',last.label||'—');set('t-date','분석일 '+last.date);set('t-score',last.score!=null?(last.score>0?'+':'')+last.score:'—');
 set('t-add',last.averaging_down||'미확인');
 const checks=last.checks||[];
 $('technical-checks').innerHTML=checks.length?checks.map(x=>`<div class="check"><span class="check-icon ${escapeHtml(x.status)}">${x.status==='positive'?'✓':x.status==='negative'?'×':'?'}</span><div><b>${escapeHtml(x.name)}</b><p>${escapeHtml(x.detail||({positive:'상승 방향',negative:'약세 방향',unknown:'데이터 부족',caution:'주의'}[x.status]||''))}</p></div></div>`).join(''):`<div class="blankmini">${missing}</div>`;
 const all=(d.series||[]),count=Number(state.techPeriod);
 const arr=Number.isFinite(count)&&count>0?all.slice(-count):all;
 set('technical-coverage',arr.length?`${arr[0].date} ~ ${arr.at(-1).date} · ${arr.length}거래일`:'자료 없음');
 const view=state.techView||'ma';
 const trendLines=view==='cloud'?
  [['close','종가',C.navy,2.7],['bb_upper','BB 상단',C.teal,1.6],['bb_lower','BB 하단',C.teal,1.6],['tenkan','전환선',C.orange,1.4],['kijun','기준선','#d9aa65',1.4],['cloud_a','구름 A','#787d9a',1.3],['cloud_b','구름 B','#adb0c8',1.3]]:
  [['close','종가',C.navy,3],['ma5','MA5',C.red,1.5],['ma20','MA20',C.orange,1.7],['ma60','MA60',C.teal,1.7],['ma120','MA120',C.purple,1.6],['ma200','MA200',C.grey,1.7]];
 chart('chart-technical',arr.map(x=>x.date),trendLines.map(([key,label,color,width])=>
   ({label,values:arr.map(x=>x[key]),color,width,dash:key.startsWith('cloud')?[4,3]:[]})),
   {yformat:'k',decimals:0,legend:true,xticks:8});
 chart('chart-rsi',arr.map(x=>x.date),[
   {label:'RSI(14)',color:C.orange,values:arr.map(x=>x.rsi14)},
   {label:'과열 참고 70',color:C.red,values:arr.map(()=>70),dash:[4,4],width:1},
   {label:'과매도 참고 30',color:C.grey,values:arr.map(()=>30),dash:[4,4],width:1}
 ],{decimals:1,yOptions:{min:0,max:100},xticks:6,legend:true});
 chart('chart-macd',arr.map(x=>x.date),[
   {label:'MACD선',values:arr.map(x=>x.macd),color:C.navy,width:2},
   {label:'시그널선',values:arr.map(x=>x.macd_signal),color:C.orange,width:1.7},
   {label:'히스토그램',values:arr.map(x=>x.macd_hist),color:C.teal,type:'bar',background:'rgba(38,117,107,0.29)',width:1}
 ],{legend:true,decimals:1,xticks:6,smooth:0});
 chart('chart-volume',arr.map(x=>x.date),[
   {label:'거래량',values:arr.map(x=>x.volume??null),color:C.grey,type:'bar',background:'rgba(116,133,176,0.35)'},
   {label:'20일 평균',values:arr.map(x=>x.volume_ma20??null),color:C.orange,width:2}
 ],{legend:true,decimals:0,xticks:6,smooth:0,yOptions:{min:0}});
 const current=arr.at(-1);
 const displayPrice=v=>v==null?'미확인':'₩'+fmt(v);
 if(current){
   set('technical-volume-note','오늘 거래량 / 직전 20거래일 평균: '+(current.volume_ratio_prior20==null?'미확인':fmt(current.volume_ratio_prior20,2)+'배')+' · 비교 평균에서 오늘을 제외합니다. 장중 자료는 하루 전체 거래량과 직접 비교하기 어렵습니다.');
   $('technical-position').innerHTML=[['직전 20일 고가',displayPrice(current.prior20_high)],['직전 20일 저가',displayPrice(current.prior20_low)],['20일선 이격',signed(pct(current.close,current.ma20))],['ATR / 종가',current.atr_pct==null?'미확인':fmt(current.atr_pct,2)+'%']].map(([k,v])=>`<span>${escapeHtml(k)} <strong>${escapeHtml(v)}</strong></span>`).join('');
 }
 const t=arr.at(-1);if(t){$('t-short-metrics').innerHTML=[['RSI(14)',t.rsi14!=null?fmt(t.rsi14,1):null],['MACD',t.macd!=null?fmt(t.macd,1):null],['MACD 히스토그램',t.macd_hist!=null?fmt(t.macd_hist,1):null],['BB 하단',t.bb_lower!=null?'₩'+fmt(t.bb_lower):null],['BB 상단',t.bb_upper!=null?'₩'+fmt(t.bb_upper):null],['ATR(14)',t.atr14!=null?'₩'+fmt(t.atr14):null]].map(([a,b])=>`<span>${escapeHtml(a)} <strong>${escapeHtml(b||'—')}</strong></span>`).join('')}
}
function trendsURL(country){
 const words=state.demand?.trends_terms||{};
 const localFallback={BR:['medicube','medicube pdrn','AGE-R','medicube collagen','skin booster'],
   AR:['medicube','medicube pdrn','AGE-R','medicube collagen','skinbooster'],
   CL:['medicube','polinucleótidos','ADN de salmón','Rejuran','skinbooster']};
 const terms=localFallback[country]?(words[country]||localFallback[country]):
   ['AE','SA','EG','QA','KW'].includes(country)?words.ME:words.default;
 const q=(terms||['medicube']).slice(0,5).join(',');return 'https://trends.google.com/trends/explore?date='+encodeURIComponent('2026-05-01 '+today())+'&geo='+encodeURIComponent(country)+'&q='+encodeURIComponent(q);
}
function renderLatinAmerica(){
 // Keep the South America-only comparison out of US/Europe/Asia/Middle East views.
 const region=$('latam-region');
 if(region)region.hidden=!['BR','AR','CL'].includes(state.country);
 const el=$('latam-overview');if(!el)return;
 const d=state.demand||{};
 const markets=countryMarkets();
 el.innerHTML=['BR','AR','CL'].map(cc=>{
   const market=markets.find(x=>x.code===cc)||{};
   const rows=(d.trends||[]).filter(x=>x.country===cc&&
     String(x.term||'').toLowerCase()==='medicube').slice().sort((a,b)=>a.date.localeCompare(b.date));
   const last=rows.at(-1);
   const snaps=rankSnapshots().filter(x=>x.country===cc).slice().sort((a,b)=>a.date.localeCompare(b.date));
   const snap=snaps.at(-1);
   const amazon=market.amazon?(snap?'Beauty Top50 · '+snap.date+' · 확정 '+snap.verified_count+' / 제목 후보 '+snap.candidate_count:'Amazon Top50 첫 수집 전'):'독립 Amazon 마켓 없음';
   const trend=last?'검색 관심도 '+fmt(last.index)+'/100 · '+last.date:'Google Trends 첫 수집 전';
   return '<button type="button" class="latam-country" data-latam-country="'+cc+
     '" aria-pressed="'+(state.country===cc)+'">'+
     '<strong>'+escapeHtml(market.name||cc)+'</strong>'+
     '<span>'+escapeHtml(trend)+'</span>'+
     '<small>'+escapeHtml(amazon)+'</small></button>';
 }).join('');
}
function renderDemand(){if(window.APR_RESEARCH)window.APR_RESEARCH.renderTrends(researchContext());const d=state.demand||{countries:countryMarkets(),amazon:[],trends:[],retailers:[],retail:[],watchlist:[]};
 const c=state.country,p=state.product,market=countryMarkets().find(x=>x.code===c);
 renderLatinAmerica();
 const observed=rankSnapshots().filter(x=>x.country===c).slice().sort((a,b)=>a.date.localeCompare(b.date));
 const mostRecent=observed.length?observed[observed.length-1]:null;
 set('amazon-quick-count',market&&!market.amazon?'독립 마켓 없음':mostRecent?'확정 '+mostRecent.verified_count+' · 후보 '+mostRecent.candidate_count:'미수집');
 set('amazon-quick-date',mostRecent?mostRecent.date+' · 50/50개 응답 검증':'관측된 날짜 없음');
 const chosen=observed.flatMap(s=>(s.items||[]).filter(x=>p==='all'||x.asin===p).map(x=>({...x,date:s.date})));
 const days=[...new Set(observed.map(x=>x.date))].sort();
 const asins=[...new Set(chosen.map(x=>x.asin))];
 chart('chart-amazon',days,asins.slice(0,8).map((asin,i)=>({
   label:(chosen.find(x=>x.asin===asin)?.title||asin).slice(0,32),
   values:days.map(day=>chosen.find(x=>x.date===day&&x.asin===asin)?.rank??null),
   color:[C.teal,C.navy,C.orange,C.purple,C.grey,C.red][i%6]
 })),{yOptions:{reverse:true,min:1,max:50},legend:true,decimals:0});
 set('amazon-meta','Beauty Top50 안에서만 비교');
 set('amazon-coverage-detail','국가·카테고리·ASIN이 같은 이전 완전 수집과 비교합니다. 제목 표기 후보와 확인 브랜드를 구분합니다.');
 $('amazon-latest').innerHTML='';
 set('amazon-empty','미수집·실패·Top50 밖 순위는 빈칸입니다. 판매량이나 51위로 환산하지 않습니다.');
 $('amazon-link').href=market?.amazon?'https://www.'+market.amazon+'/s?k=medicube':trendsURL(c);
 $('amazon-link').textContent=market?.amazon?'현지 아마존 상품 검색 ↗':'독립 마켓 없음';
 const trend=(d.trends||[]).filter(x=>x.country===c);const terms=[...new Set(trend.map(x=>x.term))].slice(0,6);
 const trendDays=[...new Set(trend.map(x=>x.date))].sort();
 set('trends-meta',trend.length+'개 확인 · '+(d.api_mode==='free_api_sh'?'무료 API/CSV':'공식 CSV')+(terms.length?' · '+terms.length+'개 검색어':''));
 if(trendDays.length)chart('chart-trends',trendDays,terms.map((term,i)=>({label:term,values:trendDays.map(day=>trend.find(z=>z.date===day&&z.term===term)?.index??null),color:[C.teal,C.navy,C.orange,C.purple,C.grey,C.red][i%6]})),{decimals:1,legend:true,yOptions:{min:0,max:100}});
 else chart('chart-trends',[],[]);
 $('trends-empty').textContent=trendDays.length?'각 CSV의 재정규화 기준이 같을 때만 비교할 수 있습니다.':missing+' 검색어별 관심도는 공식 트렌드 페이지에서 확인하세요.';
 $('trends-link').href=trendsURL(c);
 const ret=(d.retailers||[]).slice().sort((a,b)=>(b.country===c?1:0)-(a.country===c?1:0));
 const refs=state.reference||{},collection=refs.collection||{};
 $('retailer-grid').innerHTML=ret.map(x=>{
   const metrics=[...(d.retail||[]),...(refs.retail||[])].filter(z=>(z.retailer===x.id||z.retailer===x.name)&&z.eligible_for_trend!==false&&!String(z.metric||'').endsWith('_bought_lower'));
   const reviews=(refs.product_review_history||[]).filter(z=>z.retailer===x.id&&z.verified);
   const last=[...metrics,...reviews].sort((a,b)=>String(a.date).localeCompare(String(b.date))).at(-1);
   const failed=(collection.failures||[]).some(z=>String(z).startsWith(x.id+':'));
   const status=last?'공개 지표 관찰 '+last.date:'공개 지표 미수집';
   return `<div class="retailer"><small>${escapeHtml(x.country)} / RETAIL</small><b>${escapeHtml(x.name)}</b><p>${escapeHtml(status)}${failed?' · 최근 자동 수집 실패':''}</p><p>실제 점포 매출·판매량 미확보</p><a href="${validLink(x.url)}" target="_blank" rel="noopener noreferrer">판매처·검색 페이지 보기 ↗</a></div>`;
 }).join('');
 const trendLast=trend.map(x=>String(x.date||'')).sort().at(-1);
 const failures=collection.failures||[];
 $('demand-sources').innerHTML=[['Amazon Beauty Top50','Decodo · 월·수·금·토·일 07:30 KST 예약 실행에만 수집 · '+(state.top50?.status||'수집 준비 중')],['브랜드 판정','상품명 표기만 확인된 항목은 후보이며 확정 브랜드 수와 분리합니다.'],['Google Trends',trend.length+'개 값 · 마지막 관측 '+(trendLast||'없음')],['리테일 수집 상태',failures.length?'일부 실패':collection.last_attempt_utc||'미확인']].map(([a,b])=>`<div class="source-state"><span>${escapeHtml(a)}</span><b>${escapeHtml(b)}</b></div>`).join('');
 renderTop100();
 renderRetailReferences();
}
function renderTop100(){
 const c=state.country,market=countryMarkets().find(x=>x.code===c);
 const obs=rankSnapshots().filter(x=>x.country===c).sort((a,b)=>a.date.localeCompare(b.date));
 const last=obs.at(-1), check=state.top50?.latest_checks?.[c];
 $('top100-url').href=market?.amazon?'https://www.'+market.amazon+'/gp/bestsellers/beauty/':trendsURL(c);
 $('top100-url').textContent=market?.amazon?'Amazon Beauty 원문 ↗':'독립 마켓 없음';
 $('top100-external-summary').innerHTML=last?.brands?Object.entries(last.brands).map(([key,b])=>'<div><b>'+escapeHtml(b.label)+'</b><p>브랜드 확인 '+b.verified_count+' · 상품명 후보 '+b.candidate_count+'</p></div>').join(''):'';
 chart('chart-top100',obs.map(x=>x.date),[
  {label:'브랜드 확인',values:obs.map(x=>x.verified_count),color:C.teal},
  {label:'상품명 표기 후보',values:obs.map(x=>x.candidate_count),color:C.orange}
 ],{legend:true,decimals:0,yOptions:{min:0,max:50}});
 set('top100-date',last?.date||'관측 없음');
 set('top100-count',last?'확정 '+last.verified_count+'개 · 후보 '+last.candidate_count+'개':'미수집');
 set('top100-coverage',last?'응답 50/50개 순위·ASIN·상품명 검증':'수집 준비 중');
 set('top100-quality',last?'Amazon 원문 실시간 대조와 브랜드 확인은 별도입니다. '+(check?.status==='complete_50'?'':('최근 상태: '+(check?.status||'미확인'))):market?.amazon?'첫 예약 수집 대기 · 월·수·금·토·일 07:30 KST':'독립 Amazon 마켓이 없어 수집하지 않습니다.');
 set('top100-entries',last?.previous_observed_at_utc?'비교 관측: '+last.previous_observed_at_utc+' · 목록에서 사라진 상품 '+last.exited.length+'개':'이전 완전 수집 없음 · 진입·이탈 판정 보류');
 $('top100-items').innerHTML=last?(last.items.map(x=>{
  const change=x.rank_change==null?(x.movement==='entered_top50'?'Top50 진입':'첫 관측'):(x.rank_change>0?'▲ '+x.rank_change:x.rank_change<0?'▼ '+Math.abs(x.rank_change):'변동 없음');
  return '<a href="'+validLink('https://www.'+market.amazon+'/dp/'+x.asin)+'" target="_blank" rel="noopener noreferrer"><b class="rank-num">#'+fmt(x.rank)+'</b><span class="item-title">'+escapeHtml(x.title)+'<small>'+escapeHtml(x.asin)+' · '+escapeHtml(change)+' · '+(x.brand_status==='verified'?'브랜드 확인':'상품명 표기 후보')+'</small></span></a>';
 }).join('')||'<div class="blankmini">이 완전 수집 목록에 확인 브랜드·상품명 후보가 없습니다.</div>'):'<div class="blankmini">미수집은 해당 브랜드 0개라는 뜻이 아닙니다.</div>';
 if(last?.exited?.length)$('top100-items').innerHTML+=last.exited.map(x=>'<div class="blankmini">'+escapeHtml(x.title)+' · '+escapeHtml(x.asin)+' · 이전 #'+fmt(x.rank)+' → 이번 Top50 밖 (현재 순위 미확인)</div>').join('');
}

function renderRetailReferences(){
 const element=$('retail-signal-list');if(!element)return;
 const refs=state.reference?.retail||[];
 if(!refs.length){element.innerHTML='<div class="blankmini">아직 확인 가능한 판매처 실측 자료가 없습니다.</div>';return;}
 const latest=new Map();
 for(const x of refs){const key=(x.retailer||'')+'|'+(x.country||'')+'|'+(x.metric||'');
   const old=latest.get(key);if(!old||String(old.date||'')<String(x.date||''))latest.set(key,x);}
 const grouped=[...latest.values()].sort((a,b)=>String(a.country||'').localeCompare(String(b.country||''))||String(a.retailer||'').localeCompare(String(b.retailer||''))||String(a.metric||'').localeCompare(String(b.metric||'')));
 const labelName={ulta:'Ulta Beauty',target:'Target',boots:'Boots UK','watsons-sa':'Watsons Saudi','niceone-sa':'Nice One Saudi',kinegun:'KINEGUN'};
 element.innerHTML=grouped.map(x=>{
   const excluded=x.eligible_for_trend===false||String(x.metric||'').endsWith('_bought_lower');
   const metric=excluded?'검증 제외':x.display||((x.value??'')+'');
   return '<article class="retail-signal"><div class="signal-main"><div class="signal-head">'+
     '<small>'+escapeHtml((x.country||'')+' / '+(labelName[x.retailer]||x.retailer||'판매처'))+'</small>'+
     '<span>'+escapeHtml(x.date||'날짜 미확인')+'</span></div>'+
     '<b>'+escapeHtml(x.label||x.metric||'판매처 관찰')+'</b>'+
     '<p>'+escapeHtml(x.scope||'')+'</p>'+
     '<p class="signal-note">'+escapeHtml(x.note||'')+'</p>'+
     '<a href="'+validLink(x.source_url)+'" target="_blank" rel="noopener noreferrer">공식 자료 확인 ↗</a></div>'+
     '<strong class="signal-value">'+escapeHtml(metric)+'</strong></article>';
 }).join('');
}
function secOfficialLink(url){
 const u=validLink(url);
 try {
  const parsed=new URL(u);
  return parsed.protocol==='https:' && parsed.hostname==='www.sec.gov' &&
         parsed.pathname.startsWith('/Archives/edgar/data/919160/')?u:'#';
 } catch{return '#'}
}
function renderKbtySec(){
 const data=state.kbtySec||{};
 const filings=Array.isArray(data.filings)?data.filings:[];
 const briefing=Array.isArray(data.briefing)?data.briefing:[];
 const watchlist=Array.isArray(data.watchlist)?data.watchlist:[];
 set('sec-latest-date',data.latest_verified_filing_date||'공시 확인 전');
 set('sec-last-checked',data.last_successful_check_utc?
   data.last_successful_check_utc.slice(0,16).replace('T',' ')+' UTC':
   '자동 확인 전 · 기존 공시자료');
 set('sec-monitor-status',data.sec_monitor_status||
     'SEC 자료를 불러올 수 없어 기존 KBTY 공식자료만 유지합니다.');
 const briefEl=$('sec-briefing');
 if(briefEl)briefEl.innerHTML=briefing.length?briefing.map(x=>
   '<article class="sec-brief-card"><h4>'+escapeHtml(x.title)+'</h4>'+
   '<p>'+escapeHtml(x.summary)+'</p>'+
   '<p class="sec-implication"><strong>APR 관점</strong> '+escapeHtml(x.implication)+'</p>'+
   '</article>').join(''):
   '<p class="subtle">아직 검증된 투자설명서 요약이 없습니다.</p>';
 const filingEl=$('sec-filings');
 if(filingEl)filingEl.innerHTML=filings.length?filings.slice(0,24).map(item=>{
   const href=secOfficialLink(item.source_url);
   const label=escapeHtml(item.review_level||'KBTY 시리즈 확인');
   return '<article class="sec-filing">'+
     '<div class="sec-filing-meta"><span>'+escapeHtml(item.filed_date||'제출일 미확인')+
     ' · '+escapeHtml(item.form||'')+'</span><small>'+label+'</small></div>'+
     '<strong>'+escapeHtml(item.title_ko||'SEC 제출자료')+'</strong>'+
     '<p>'+escapeHtml(item.summary_ko||'')+'</p>'+
     (item.change_ko?'<p class="sec-filing-change">확인 사항: '+escapeHtml(item.change_ko)+'</p>':'')+
     '<a href="'+href+'" target="_blank" rel="noopener noreferrer">SEC 공시 원문 확인 ↗</a>'+
     '</article>';
 }).join(''):'<p class="subtle">KBTY 시리즈로 확인된 SEC 공시가 없습니다.</p>';
 const watchEl=$('sec-watchlist');
 if(watchEl)watchEl.innerHTML=watchlist.map(x=>
   '<div class="sec-watch-row"><strong>'+escapeHtml(x.title||'추적 항목')+'</strong>'+
   '<p>'+escapeHtml(x.desc||'')+'</p></div>').join('')||
   '<p class="subtle">추적할 공시 후속자료가 없습니다.</p>';
 const filingLink=$('sec-filer-link');
 if(filingLink)filingLink.href='https://www.sec.gov/edgar/browse/?CIK=919160';
}
function renderEtf(){const e=state.kbty;if(!e)return;
 renderKbtySec();
 set('kbty-status',e.status||'상태 미확인');set('e-price',e.latest_price_usd!=null?'$'+fmt(e.latest_price_usd,2):'—');set('e-price-date',(e.price_date||'거래 전 또는 시세 미확인')+' · Yahoo 비공식 시세');
 set('e-aum',e.aum_usd!=null?'$'+fmt(e.aum_usd,0):'—');set('e-apr',e.apr_weight_pct!=null?fmt(e.apr_weight_pct,2)+'%':'—');
 set('e-apr-date',e.apr_holding_as_of||'APR 편입비중 자료 미확인');set('e-shares',e.apr_shares!=null?fmt(e.apr_shares):'—');
 const price=(e.price_history||[]).filter(x=>x.close_usd!=null);chart('chart-etf',price.map(x=>x.date),[{label:'KBTY USD',values:price.map(x=>x.close_usd),color:C.navy}],{decimals:2});
 $('etf-price-empty').textContent=price.length?'':missing+' 공식 상장 후 확인합니다.';
 const au=(e.aum_history||[]).filter(x=>x.aum_usd!=null);chart('chart-aum',au.map(x=>x.date),[{label:'AUM ($)',values:au.map(x=>x.aum_usd),color:C.teal}],{decimals:0});
 $('etf-aum-empty').textContent=au.length?'':missing+' 운용사 AUM 자료 미확보. 발표 여부와 별개입니다.';
 const holdings=(e.holdings||[]).sort((a,b)=>b.weight_pct-a.weight_pct);
 $('etf-holdings').innerHTML=holdings.length?holdings.slice(0,12).map(x=>`<div class="holding"><span>${escapeHtml(x.name||x.ticker)}</span><b>${fmt(x.weight_pct,2)}%</b></div>`).join(''):
  '<div class="blankmini">검증한 운용사 보유종목 CSV가 입력되지 않았습니다. 자료 미확보를 미편입(0%)이나 미공개로 단정하지 않습니다.</div>';
}
function renderNews(){
 const d=state.news;if(!d)return;
 const events=(d.verified_events||[]).slice().sort((a,b)=>b.date.localeCompare(a.date));
 $('verified-events').innerHTML=events.map(x=>'<article class="event"><span class="tag">'+escapeHtml(x.date)+' · '+escapeHtml(x.country)+' · '+escapeHtml(x.stage)+'</span><h3>'+escapeHtml(x.title)+'</h3><p>'+escapeHtml(x.summary||'')+'</p><a href="'+validLink(x.source_url)+'" target="_blank" rel="noopener noreferrer">원문 확인 ↗</a></article>').join('');
 const word=$('news-filter')?.value||'all';
 const all=(d.items||[]),items=all.filter(x=>word==='all'||(x.category||'').includes(word));
 const translated=items.filter(x=>x.title_ko&&x.summary_ko).length;
 const status=$('news-korean-status');
 if(status)status.textContent='한국어 정리 '+translated+'/'+items.length+'건 · 기사 제목 기반 핵심 정리 · 원문 전문은 별도 확인';
 $('news-stack').innerHTML=items.length?items.slice(0,36).map(x=>{
  const korean=Boolean(x.title_ko&&x.summary_ko);
  const title=escapeHtml(korean?x.title_ko:x.title);
  const summary=korean?escapeHtml(x.summary_ko):'무료 번역이 아직 준비되지 않았습니다. 아래 원문 제목·출처를 확인하세요.';
  const publisher=escapeHtml(x.publisher||'현지 보도');
  const origin=escapeHtml(x.title||'');
  const date=escapeHtml(x.published||'날짜 미확인');
  const country=escapeHtml(x.country||'');
  const category=escapeHtml(x.category||'');
  return '<article class="news-card">'+
    '<small>'+date+' · '+country+' · '+category+' · '+publisher+'</small>'+
    '<strong>'+title+'</strong>'+
    '<p class="news-korean-brief">'+summary+'</p>'+
    '<div class="news-status">제목 기반 요약 · 실제 판매·허가·실적은 공식 자료 확인 필요</div>'+
    (korean?'<details class="news-original"><summary>원문 제목 보기</summary><p>'+origin+'</p></details>':'')+
    '<a class="news-article-link" href="'+validLink(x.url)+'" target="_blank" rel="noopener noreferrer">현지 기사 원문 확인 ↗</a>'+
    '</article>';
 }).join(''):
 '<div class="panel padded" style="grid-column:1/-1"><p class="subtle">현재 저장된 RSS 기사 실측이 없습니다. 자동 갱신이 성공하면 날짜별로 여기에 누적됩니다.</p><a class="minor-button" href="https://news.google.com/search?q=medicube%20Chile%20Kinegun&hl=es-419&gl=CL&ceid=CL%3Aes-419" target="_blank" rel="noopener">칠레 스페인어 뉴스 직접 검색 ↗</a></div>';
}
const FREIGHT_ROUTES=[
 {key:'us_west',name:'미국 서부',group:'long',color:C.navy},
 {key:'us_east',name:'미국 동부',group:'long',color:C.teal},
 {key:'eu',name:'유럽연합',group:'long',color:C.purple},
 {key:'middle_east',name:'중동',group:'long',color:C.orange},
 {key:'china',name:'중국',group:'near',color:C.navy},
 {key:'japan',name:'일본',group:'near',color:C.teal},
 {key:'vietnam',name:'베트남',group:'near',color:C.purple}
];
function previousMonth(month,offset){
 if(!/^\d{4}-(0[1-9]|1[0-2])$/.test(String(month)))return null;
 const d=new Date(month+'-01T00:00:00Z');
 d.setUTCMonth(d.getUTCMonth()-offset);
 return d.toISOString().slice(0,7);
}
function renderKitaRates(){
 const k=state.kitaRates||{}, customs=state.market?.logistics||{};
 const all=(k.sea_routes||[]).filter(r=>r?.origin==='Busan'&&r.month&&
      ['Long Beach','New York'].includes(r.destination));
 const west=all.filter(r=>r.destination==='Long Beach').slice().sort((a,b)=>a.month.localeCompare(b.month));
 const east=all.filter(r=>r.destination==='New York').slice().sort((a,b)=>a.month.localeCompare(b.month));
 const lastW=west.at(-1),previousW=west.at(-2);
 const lastE=east.at(-1),previousE=east.at(-2);
 const commonMonths=[...new Set(all.map(r=>r.month))].sort();
 const wm=new Map(west.map(r=>[r.month,r]));
 const em=new Map(east.map(r=>[r.month,r]));
 chart('chart-kita-sea',commonMonths,[
    {label:'미국 서안 · 롱비치 FEU',values:commonMonths.map(m=>wm.get(m)?.feu_usd??null),color:C.navy},
    {label:'미국 동안 · 뉴욕 FEU',values:commonMonths.map(m=>em.get(m)?.feu_usd??null),color:C.teal}
 ],{legend:true,decimals:0,xticks:10});
 const eastDirect=lastE?.source_type==='KITA_RADIS_PUBLIC_HTML'||
      lastE?.source_type==='KITA_RADIS_OFFICIAL_BULLETIN';
 const sameMonth=lastW&&lastE&&lastW.month===lastE.month;
 set('kita-feu',lastW?.feu_usd!=null?'$'+fmt(lastW.feu_usd):'—');
 set('kita-east-feu',lastE?.feu_usd!=null?'$'+fmt(lastE.feu_usd):'—');
 set('kita-feu-mom',lastW&&previousW&&previousW.month===previousMonth(lastW.month,1)
   ?signed(pct(lastW.feu_usd,previousW.feu_usd))+' 전월대비':'전월 비교월 미확인');
 set('kita-east-mom',lastE&&previousE&&previousE.month===previousMonth(lastE.month,1)
   ?signed(pct(lastE.feu_usd,previousE.feu_usd))+' 전월대비':'전월 비교월 미확인');
 set('kita-spread',sameMonth?'$'+fmt(lastE.feu_usd-lastW.feu_usd):'—');
 set('kita-teu',lastW?.teu_usd!=null?'$'+fmt(lastW.teu_usd):'—');
 set('kita-asof','KITA 미 서안 '+(lastW?.month||'미수집')+
     ' / 미 동안 '+(lastE?.month||'미수집')+
     ' · 시장참고 USD/FEU, 공시 조건·할증료에 유의');
 set('kita-lead-lag','관세청 후행 운송비용 기준월 '+
      (customs.last_verified_month||'미수집')+
      ' · KITA 시장 참고운임은 APR 계약운임 또는 관세청 신고평균과 다름');
 const sourceName=r=>r?.source_type==='KITA_RADIS_PUBLIC_HTML'||
      r?.source_type==='KITA_RADIS_OFFICIAL_BULLETIN'?'KITA 직접 확인':
      r?.source_type?.includes('SECONDARY')?'2차 출처 · KITA 인용':'기존 확인 스냅샷';
 const makeRow=(r,prev,reg,port)=>{
   if(!r)return '<tr><td>'+reg+'</td><td>'+port+'</td><td colspan="4">공식 기록 없음</td></tr>';
   const mom=prev&&prev.month===previousMonth(r.month,1)?signed(pct(r.feu_usd,prev.feu_usd)):'—';
   return '<tr><td>'+reg+'</td><td>'+port+'</td><td>'+escapeHtml(r.month)+
      '</td><td>$'+fmt(r.feu_usd)+'</td><td>'+mom+'</td><td><a href="'+
      validLink(r.source_url||k.sea_source_url)+'" target="_blank" rel="noopener noreferrer">'+
      escapeHtml(sourceName(r))+' ↗</a></td></tr>';
 };
 const tb=$('kita-route-table');
 if(tb)tb.innerHTML=makeRow(lastW,previousW,'미국 서안','롱비치')+
                      makeRow(lastE,previousE,'미국 동안','뉴욕');
 const wcount=west.filter(r=>r.source_type==='KITA_RADIS_PUBLIC_HTML'||
                            r.source_type==='KITA_RADIS_OFFICIAL_BULLETIN').length;
 const ecount=east.filter(r=>r.source_type==='KITA_RADIS_PUBLIC_HTML'||
                            r.source_type==='KITA_RADIS_OFFICIAL_BULLETIN').length;
 const secondary=east.filter(r=>r.source_type?.includes('SECONDARY')).length;
 set('kita-quality','서안 KITA 직접 조회 '+wcount+'개월 · 동안 직접 확인 '+ecount+
   '개월 / KITA 인용 2차 출처 '+secondary+'개월. '+
   (k.latest_access_ok===false?'최근 서안 자동 접속 실패 · 기존 실측 유지. ':'')+
   (!eastDirect&&lastE?'동안 최신 월은 KITA 직접 확인 전 · 출처 신뢰등급이 서안과 다릅니다. ':'')+
   (k.east_secondary_access_ok===true?'동안 2차 공개자료 자동 확인 성공. ':k.east_secondary_access_ok===false?'동안 2차 공개자료 최근 접근 실패. ':''));
 set('kita-source-note',
   '권역 대표항로만 비교합니다. KITA 공식 해상수출 공지 자료의 뉴욕/노퍽/서배너 값은 일부 동일하나 전국 동일 운임은 아닙니다. '+
   '동안 '+(lastE?.month||'미수집')+' 값의 출처: '+sourceName(lastE)+
   '. 일부 KITA 월간 공지(예: 2026년 4월)는 할증료 제외 조건으로 안내돼 월간 비교에 유의해야 합니다.'+
   ' 동·서부 최신 비교도 출처 등급이 서로 다를 수 있습니다. 중간 미수집 월은 보간하지 않습니다.');
}
function renderLogistics(){
 renderKitaRates();
 const region=state.reference?.regional_channels||{};
 const data=region.regions||[];
 chart('chart-region',data.map(x=>x.name),[{label:'2026 2Q · IR 공시',values:data.map(x=>x.q2),color:C.navy,background:'#193a5a'},
 {label:'2026 3Q · 국내 실적 / 해외 비중환산 추정',values:data.map(x=>x.q3),color:C.teal,background:'#0b917f'}],{type:'bar',legend:true});
 $('offline-table').innerHTML='<table><thead><tr><th>지역</th><th>2Q 오프라인</th><th>3Q 오프라인</th><th>지역 매출 QoQ (추정)</th></tr></thead><tbody>'+
   data.filter(x=>x.offline_q2!=null).map(x=>'<tr><td>'+escapeHtml(x.name)+'</td><td>약 '+fmt(x.offline_q2)+'%</td><td>약 '+fmt(x.offline_q3)+'%</td><td>'+signed(pct(x.q3,x.q2))+'</td></tr>').join('')+'</tbody></table>'+
   '<p class="under-note">'+escapeHtml(region.note||'지역별 원문 대조 자료 미확보')+'</p>'+
   (region.sources||[]).map(x=>'<a href="'+validLink(x.url)+'" target="_blank" rel="noopener noreferrer">'+escapeHtml(x.label)+' ↗</a>').join(' · ');
 const log=state.market?.logistics||{};
 const sea=(log.sea||[]).filter(x=>x?.month).slice().sort((a,b)=>String(a.month).localeCompare(String(b.month)));
 const seaByMonth=new Map(sea.map(x=>[x.month,x]));
 const lastSea=sea.at(-1);
 const last=lastSea?.month||'미수집';
 const message=log.last_fetch_failed?' · 최근 공식 조회 실패: 과거 확인값 유지':'';
 set('freight-asof','최근 보유 월 '+last+' · 단위: 천원/2TEU (40피트) · '+
   (log.source||'관세청 해상수출 운송비용')+' · 월간 후행지표'+message);
 const sourceLink=$('freight-source-url');
 if(sourceLink)sourceLink.href=validLink(log.source_url||
    'https://www.customs.go.kr/kcs/na/ntt/selectNttList.do?bbsId=1362&mi=2891');
 const group=$('freight-group')?.value==='near'?'near':'long';
 const selected=FREIGHT_ROUTES.filter(x=>x.group===group);
 chart('chart-sea',sea.map(x=>x.month),selected.map(route=>({
   label:route.name,values:sea.map(x=>x[route.key]??null),color:route.color
 })),{decimals:0,legend:true});
 const rows=FREIGHT_ROUTES.map(route=>{
   const observed=sea.filter(x=>x[route.key]!=null&&Number.isFinite(Number(x[route.key]))).at(-1);
   if(!observed)return '<tr><td>'+escapeHtml(route.name)+'</td><td>—</td><td colspan="4">해당 항로 공식 관측값 없음</td></tr>';
   const previous=seaByMonth.get(previousMonth(observed.month,1));
   const lastYear=seaByMonth.get(previousMonth(observed.month,12));
   // Publication rates take precedence: later Customs releases may revise
   // preceding months, so recomputed movement can differ from official MoM.
   const mom=observed.reported_mom_pct?.[route.key] ??
     (previous?.[route.key]!=null?pct(observed[route.key],previous[route.key]):null);
   const yoy=observed.reported_yoy_pct?.[route.key] ??
     (lastYear?.[route.key]!=null?pct(observed[route.key],lastYear[route.key]):null);
   const source=observed.source_url
     ?'<a href="'+validLink(observed.source_url)+'" target="_blank" rel="noopener noreferrer">원문 ↗</a>'
     :'<span title="해당 월 공식 링크 재검증 전">재검증 전</span>';
   return '<tr><td>'+escapeHtml(route.name)+'</td><td>'+escapeHtml(observed.month)+
     '</td><td>'+fmt(observed[route.key])+'</td><td>'+signed(mom)+
     '</td><td>'+signed(yoy)+'</td><td>'+source+'</td></tr>';
 });
 const tb=$('freight-route-table');if(tb)tb.innerHTML=rows.join('');
 const gaps=log.unverified_months||[];
 set('freight-history-quality',
   '원문 기준 월 '+sea.filter(x=>x.source_url).length+'개 확인 / 전체 보유 '+sea.length+
   '개월 · 원문 재검증 전/누락 월: '+(gaps.length?gaps.join(', '):'확인된 누락 없음')+
   (log.history_backfill_errors?.length?' · 과거 자료 일부 접근/파싱 실패':'')+
   (log.last_fetch_failed?' · 최신 재조회 실패':'')+
   '. 증감률은 관세청 해당 월 공식 발표치 우선, 미확인 경우에만 보유 월간 수치로 계산. 사후 통계 정정으로 단순 계산과 차이가 날 수 있습니다.');
 const errs=state.status?.errors||[];
 set('diagnostic-date',state.status?.generated_at_utc||'최초 데이터 수집 전');
 $('diagnostic-errors').innerHTML=errs.length?errs.slice(0,12).map(x=>'<div class="check"><span class="check-icon caution">!</span><div><b>데이터 접근 또는 출처 확인</b><p>'+escapeHtml(x)+'</p></div></div>').join(''):'<div class="check"><span class="check-icon positive">✓</span><div><b>저장된 자료의 필수 오류 미발견</b><p>각 자료의 기준일이 최신인지 별도로 확인하세요.</p></div></div>';
}
function fillProductChoices(){
 const observed=rankSnapshots().filter(s=>s.country===state.country).flatMap(s=>s.medicube_listings||[]);
 const names=new Map();for(const x of observed)names.set(x.asin,x.title||x.asin);
 for(const x of (state.demand?.amazon||[]).filter(z=>z.country===state.country))if(x.asin&&!names.has(x.asin))names.set(x.asin,x.product||x.asin);
 const sel=$('product');if(!sel)return;
 sel.innerHTML='<option value="all">선택 브랜드 전체 상품</option>'+[...names].map(([asin,name])=>'<option value="'+escapeHtml(asin)+'">'+escapeHtml(name.slice(0,55))+'</option>').join('');
 if(state.product!=='all'&&!names.has(state.product))state.product='all';sel.value=state.product;
}
function initControls(){
 const brand=$('apr-brand');if(brand)brand.addEventListener('change',()=>{state.brand=brand.value;state.product='all';fillProductChoices();renderDemand();});
 const d=state.demand||{};const country=$('country');country.innerHTML=countryMarkets().map(x=>`<option value="${escapeHtml(x.code)}">${escapeHtml(x.region)} · ${escapeHtml(x.name)}</option>`).join('');
 country.value=state.country;country.addEventListener('change',()=>{state.country=country.value;fillProductChoices();renderDemand()});
 const latam=$('latam-overview');if(latam)latam.addEventListener('click',e=>{
   const node=e.target.closest?.('[data-latam-country]');const cc=node?.dataset?.latamCountry;
   if(!['BR','AR','CL'].includes(cc))return;
   state.country=cc;country.value=cc;fillProductChoices();renderDemand();
 });
 fillProductChoices();
 $('product').addEventListener('change',()=>{state.product=$('product').value;renderDemand()});
 $('period').addEventListener('change',e=>{state.period=e.target.value;renderOverview()});
 $('news-filter').addEventListener('change',renderNews);
 const period=$('technical-period');if(period)period.addEventListener('change',()=>{state.techPeriod=period.value;renderTechnical();});
 const view=$('technical-view');if(view)view.addEventListener('change',()=>{state.techView=view.value;renderTechnical();});
 const fg=$('freight-group');if(fg)fg.addEventListener('change',renderLogistics);
 const finTable=$('fin-table-kind');if(finTable)finTable.addEventListener('change',()=>{if(window.APR_RESEARCH)window.APR_RESEARCH.renderFinancials(researchContext())});
 const trendAlerts=$('trend-alerts');if(trendAlerts)trendAlerts.addEventListener('click',e=>{
    const node=e.target.closest?.('[data-trend-country]');
    const cc=node?.dataset?.trendCountry;
    if(!cc||!countryMarkets().some(x=>x.code===cc))return;
    state.country=cc;country.value=cc;fillProductChoices();renderDemand();
 });
 $('download-market').addEventListener('click',()=>{
  const rows=marketRows();if(!rows.length)return alert('내려받을 실제 시세 데이터가 없습니다.');
  const cols=['date','open_krw','high_krw','low_krw','close_krw','close_usd','usdkrw','eurkrw','volume'];
  const csv=[cols.join(','),...rows.map(x=>cols.map(c=>x[c]??'').join(','))].join('\n');
  const blob=new Blob(['\uFEFF',csv],{type:'text/csv;charset=utf-8'});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download='APR_278470_KRW_USD_2026-05.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);
 });
}
async function init(){
 const names=['market','technical','kbty','news','demand','status','top50','reference_signals','kbty_sec','financials','trend_signals','apr_theses','dart_ownership','dart_financials','dart_capital','kita_rates','flows','flow_reference'];const data=await Promise.all(names.map(getJSON));names.forEach((n,i)=>state[n==='reference_signals'?'reference':n==='kbty_sec'?'kbtySec':n==='trend_signals'?'trendSignals':n==='apr_theses'?'aprTheses':n==='dart_ownership'?'dartOwnership':n==='dart_financials'?'dartFinancials':n==='dart_capital'?'dartCapital':n==='kita_rates'?'kitaRates':n==='flow_reference'?'flowReference':n]=data[i]);
 const sync=state.status?.generated_at_utc;
 set('last-synced',sync?'최종 수집 '+sync.slice(0,10)+' (UTC)':'최초 클라우드 갱신 전');
 initControls();if(window.APR_SENSITIVITY)window.APR_SENSITIVITY.init(researchContext());if(window.APR_FLOWS)window.APR_FLOWS.init(researchContext());showPage(location.hash);window.addEventListener('hashchange',()=>showPage(location.hash));
}
window.addEventListener('DOMContentLoaded',init);
})();
