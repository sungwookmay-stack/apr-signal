/* APR SIGNAL • Free, static, sourced market monitor. No trading order function. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const fmt=(n,d=0)=>n==null||!Number.isFinite(Number(n))?'—':Number(n).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=(a,b)=>a!=null&&b!=null&&Number(b)!==0?(a/b-1)*100:null;
const signed=(n,d=1)=>n==null?'—':(n>0?'+':'')+fmt(n,d)+'%';
const state={market:null,tech:null,kbty:null,news:null,demand:null,status:null,financials:null,trendSignals:null,aprTheses:null,period:'all',country:'US',product:'all',nav:'overview',charts:{},top100:null,reference:null,dartOwnership:null,dartFinancials:null,dartCapital:null,techView:'ma'};
const C={navy:'#293841',teal:'#26756b',orange:'#c19561',purple:'#786a9d',grey:'#a1a9b0',red:'#bb5b63'};
const missing='실측 데이터 없음 · 확인된 값만 표시합니다.';
const minimalMarkets=[{code:'US',name:'미국',region:'북미',amazon:'amazon.com'},{code:'GB',name:'영국',region:'유럽',amazon:'amazon.co.uk'},{code:'DE',name:'독일',region:'유럽',amazon:'amazon.de'},{code:'FR',name:'프랑스',region:'유럽',amazon:'amazon.fr'},{code:'IT',name:'이탈리아',region:'유럽',amazon:'amazon.it'},{code:'ES',name:'스페인',region:'유럽',amazon:'amazon.es'},{code:'CA',name:'캐나다',region:'북미',amazon:'amazon.ca'},{code:'JP',name:'일본',region:'아시아',amazon:'amazon.co.jp'},{code:'AE',name:'아랍에미리트',region:'중동',amazon:'amazon.ae'},{code:'SA',name:'사우디아라비아',region:'중동',amazon:'amazon.sa'},{code:'EG',name:'이집트',region:'중동',amazon:'amazon.eg'},{code:'QA',name:'카타르',region:'중동',amazon:null},{code:'KW',name:'쿠웨이트',region:'중동',amazon:null},{code:'BR',name:'브라질',region:'남미',amazon:'amazon.com.br',amazon_beauty_slug:'beauty'},{code:'AR',name:'아르헨티나',region:'남미',amazon:null},{code:'CL',name:'칠레',region:'남미',amazon:null}];
function countryMarkets(){
 const actual=state.demand?.countries?.length?state.demand.countries:minimalMarkets;
 const missingMarkets=minimalMarkets.filter(x=>!actual.some(y=>y.code===x.code));
 return actual.concat(missingMarkets).map(x=>['BR','AR','CL'].includes(x.code)?{...x,region:'남미'}:x);
}
function rankSnapshots(){return state.top100?.snapshots?.length?state.top100.snapshots:(state.demand?.top100||[]);}
function set(id,val){const e=$(id);if(e)e.textContent=val;}
function safeText(s){return String(s??'');}
function escapeHtml(s){return safeText(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function validLink(url){try{let u=new URL(url);return ['https:','http:'].includes(u.protocol)?u.href:'#'}catch{return '#'}}
async function getJSON(name){try{const r=await fetch('./data/'+name+'.json?v='+Date.now(),{cache:'no-store'});if(r.ok)return await r.json()}catch{}return window.APR_BOOTSTRAP?.[name]??null}
function today(){return new Date().toISOString().slice(0,10)}
function showPage(hash){const id=(hash||location.hash||'#overview').replace('#','');state.nav=['overview','technical','financials','demand','theses','kbty','business','logistics'].includes(id)?id:'overview';document.querySelectorAll('[data-page]').forEach(x=>x.classList.toggle('active',x.dataset.page===state.nav));document.querySelectorAll('[data-nav]').forEach(x=>x.classList.toggle('active',x.dataset.nav===state.nav));document.querySelectorAll('[data-mnav]').forEach(x=>x.classList.toggle('active',x.dataset.mnav===state.nav));if(state.nav==='technical')renderTechnical();if(state.nav==='financials'&&window.APR_RESEARCH)window.APR_RESEARCH.renderFinancials(researchContext());if(state.nav==='theses'&&window.APR_RESEARCH)window.APR_RESEARCH.renderTheses(researchContext());if(state.nav==='demand'){renderDemand();if(window.APR_RESEARCH)window.APR_RESEARCH.renderRetail(researchContext());}if(state.nav==='kbty')renderEtf();if(state.nav==='business')renderNews();if(state.nav==='logistics')renderLogistics();if(state.nav==='overview')renderOverview();window.scrollTo({top:0,behavior:'instant'});}
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
function renderTechnical(){const d=state.technical,last=d?.last;
 if(!last||!last.date){set('t-decision','분석 자료 미확보');set('t-add','보류');return}
 set('t-decision',last.label||'—');set('t-date','분석일 '+last.date);set('t-score',last.score!=null?(last.score>0?'+':'')+last.score:'—');
 set('t-add',last.averaging_down||'미확인');set('t-risk-message',last.add_criteria||'구름 및 볼린저 반등 확인 필요');
 set('t-risk-price',last.risk_reference!=null?'₩'+fmt(last.risk_reference):'—');
 const checks=last.checks||[];
 $('technical-checks').innerHTML=checks.length?checks.map(x=>`<div class="check"><span class="check-icon ${escapeHtml(x.status)}">${x.status==='positive'?'✓':x.status==='negative'?'×':'?'}</span><div><b>${escapeHtml(x.name)}</b><p>${escapeHtml(x.detail||({positive:'상승 방향',negative:'약세 방향',unknown:'데이터 부족',caution:'주의'}[x.status]||''))}</p></div></div>`).join(''):`<div class="blankmini">${missing}</div>`;
 const arr=(d.series||[]).filter(x=>x.date>='2025-06-01').slice(-120);
 const view=state.techView||'ma';
 const trendLines=view==='cloud'?
  [['close','종가',C.navy,2.7],['bb_upper','BB 상단',C.teal,1.6],['bb_lower','BB 하단',C.teal,1.6],['tenkan','전환선',C.orange,1.4],['kijun','기준선','#d9aa65',1.4],['cloud_a','구름 A','#787d9a',1.3],['cloud_b','구름 B','#adb0c8',1.3]]:
  [['close','종가',C.navy,3],['ma5','MA5',C.red,1.5],['ma20','MA20',C.orange,1.7],['ma60','MA60',C.teal,1.7],['ma120','MA120',C.purple,1.6],['ma200','MA200',C.grey,1.7]];
 chart('chart-technical',arr.map(x=>x.date.slice(5)),trendLines.map(([key,label,color,width])=>
   ({label,values:arr.map(x=>x[key]),color,width,dash:key.startsWith('cloud')?[4,3]:[]})),
   {yformat:'k',decimals:0,legend:true,xticks:8});
 chart('chart-rsi',arr.map(x=>x.date.slice(5)),[
   {label:'RSI(14)',color:C.orange,values:arr.map(x=>x.rsi14)}
 ],{decimals:1,yOptions:{min:0,max:100},xticks:6});
 chart('chart-macd',arr.map(x=>x.date.slice(5)),[
   {label:'MACD선',values:arr.map(x=>x.macd),color:C.navy,width:2},
   {label:'시그널선',values:arr.map(x=>x.macd_signal),color:C.orange,width:1.7},
   {label:'히스토그램',values:arr.map(x=>x.macd_hist),color:C.teal,type:'bar',background:'rgba(38,117,107,0.29)',width:1}
 ],{legend:true,decimals:1,xticks:6,smooth:0});
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
   const amazon=market.amazon?(snap?'Beauty Top 100 관측 '+snap.date+' · '+(Number(snap.medicube_confirmed_count)>0?'메디큐브 최소 '+snap.medicube_confirmed_count+'종':'메디큐브 진입 여부 미확인')+' · 브랜드 식별 '+(snap.identity_coverage_count??'?')+'/100':'Amazon Top 100 첫 수집 전'):'독립 Amazon 마켓 없음';
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
 set('amazon-quick-count',market&&!market.amazon?'독립 마켓 없음':mostRecent?(mostRecent.coverage_complete?String(mostRecent.medicube_confirmed_count)+'개':Number(mostRecent.medicube_confirmed_count)>0?'최소 '+String(mostRecent.medicube_confirmed_count)+'개':'진입 여부 미확인'):'미수집');
 set('amazon-quick-date',mostRecent?mostRecent.date+' · '+mostRecent.coverage_count+'/100개 순위 확인':'관측된 날짜 없음');
 const confirmed=observed.flatMap(s=>(s.medicube_listings||[]).map(x=>({
    date:s.date,country:c,asin:x.asin,bsr:x.rank,title:x.title,url:x.url,
    source:'Amazon Beauty Best Sellers 목록',coverage_count:s.coverage_count
 })));
 const individual=(d.amazon||[]).filter(x=>x.country===c);
 const chosen=p==='all'?confirmed:confirmed.filter(x=>x.asin===p);
 const individualChosen=p==='all'?individual:individual.filter(x=>x.asin===p);
 const uniqueASINs=[...new Set(chosen.map(x=>x.asin))];
 const days=[...new Set(chosen.map(x=>x.date))].sort();
 const latestPerASIN=new Map();
 for(const item of chosen){const old=latestPerASIN.get(item.asin);if(!old||old.date<=item.date)latestPerASIN.set(item.asin,item);}
 const lastItems=[...latestPerASIN.values()].sort((a,b)=>a.bsr-b.bsr);
 // Beauty chart ranks and product-detail BSR are different sources; never merge their categories.
 if(days.length){
   chart('chart-amazon',days,uniqueASINs.slice(0,8).map((asin,i)=>({
      label:(latestPerASIN.get(asin)?.title||asin).replace(/^medicube\s+/i,'').slice(0,32),
      values:days.map(day=>chosen.find(x=>x.date===day&&x.asin===asin)?.bsr??null),
      color:[C.teal,C.navy,C.orange,C.purple,C.grey,C.red][i%6]
   })),{yOptions:{reverse:true,min:1},legend:uniqueASINs.length>1,decimals:0});
 }else if(individualChosen.length){
   const srt=individualChosen.slice().sort((a,b)=>a.date.localeCompare(b.date));
   const dates=[...new Set(srt.map(x=>x.date))];
   const asins=[...new Set(srt.map(x=>x.asin))];
   chart('chart-amazon',dates,asins.slice(0,8).map((asin,i)=>({
      label:asin,values:dates.map(day=>srt.find(x=>x.date===day&&x.asin===asin)?.bsr??null),
      color:[C.teal,C.navy,C.orange,C.purple,C.grey,C.red][i%6]
   })),{yOptions:{reverse:true},legend:asins.length>1});
 }else chart('chart-amazon',[],[]);
 // PDP BSR must be drawn separately from Beauty Top 100 list positions.
 // Keep one category per ASIN; do not splice distinct subcategory ranks together.
 const pdp=individualChosen.filter(x=>x.source_quality==='verified_product_rank'&&
   Number(x.bsr)>0&&x.category);
 const byPair=new Map();
 for(const x of pdp){
   const key=x.asin+'|'+x.category;
   if(!byPair.has(key))byPair.set(key,[]);
   byPair.get(key).push(x);
 }
 const byASIN=new Map();
 const looksBeauty=s=>/beauty|beauté|bellezza|belleza|schönheit|美容|ビューティ|الجمال/i.test(String(s));
 for(const [key,rows] of byPair){
   const asin=rows[0].asin, category=rows[0].category;
   const priority=(looksBeauty(category)?1000:0)+rows.length;
   if(!byASIN.has(asin)||byASIN.get(asin).priority<priority)
     byASIN.set(asin,{asin,category,rows,priority});
 }
 const pdpSeries=[...byASIN.values()].sort((a,b)=>b.rows.length-a.rows.length).slice(0,6);
 const pdpDays=[...new Set(pdpSeries.flatMap(x=>x.rows.map(r=>r.date)))].sort();
 chart('chart-amazon-pdp',pdpDays,pdpSeries.map((z,i)=>({
   label:z.asin+' · '+z.category.slice(0,24),
   values:pdpDays.map(day=>z.rows.find(x=>x.date===day)?.bsr??null),
   color:[C.teal,C.navy,C.orange,C.purple,C.grey,C.red][i%6]
 })),{yOptions:{reverse:true,min:1},legend:true,decimals:0});
 set('amazon-pdp-note',pdpDays.length?
   '실제 상품 상세페이지에서 확인된 BSR '+pdp.length+'건 · 같은 ASIN의 한 카테고리 안에서만 시계열 연결 · 값이 없는 날은 공백':
   '개별 상품 상세 BSR 아직 미수집 · 무료 PDP 조회 성공 후부터 날짜별 누적');
 set('amazon-meta','Beauty 순위 관측 '+confirmed.length+'건 · 개별 상품 BSR '+pdp.length+'건');
 set('amazon-coverage-detail',observed.length?
    ('최신 '+observed[observed.length-1].date+' · Beauty 순위 '+observed[observed.length-1].coverage_count+'/100개 확인 · '+(observed[observed.length-1].coverage_complete?'메디큐브 품목 수 확정':'상품 식별 미완료, 메디큐브 최소 확인 품목 수')):
    'Beauty 순위 수집 전 · 상품별 BSR과 집계 범위는 별도 확인');
 $('amazon-latest').innerHTML=lastItems.length?
    lastItems.slice(0,12).map(x=>'<a href="'+validLink(x.url)+'" target="_blank" rel="noopener noreferrer"><b>#'+fmt(x.bsr)+'</b><span>'+escapeHtml(x.title)+'<small> · '+escapeHtml(x.date)+' · '+escapeHtml(x.asin)+'</small></span></a>').join(''):
    '<div class="blankmini">선택한 국가·상품의 확인된 Beauty 판매순위가 아직 없습니다.</div>';
 $('amazon-empty').textContent=days.length?
    'Beauty 베스트셀러 목록에서 확인한 순위입니다. 상품 상세페이지의 BSR과 구분하며, 첫날은 점으로 표시합니다.':
    individualChosen.length?'개별 상품 BSR 관측값입니다. 카테고리가 동일한 경우에만 비교하세요.':
    '공개 목록에서 검증된 순위가 없습니다. 미확인은 0위 또는 Top 100 미진입이 아닙니다.';
 if(market&&market.amazon)$('amazon-link').href='https://www.'+market.amazon+'/s?k='+encodeURIComponent(p==='all'?'medicube':p);else $('amazon-link').href='https://trends.google.com/trends/explore';
 $('amazon-link').textContent=market?.amazon?'현지 아마존에서 제품 검색 ↗':'아마존 독립 마켓플레이스 없음';
 const trend=(d.trends||[]).filter(x=>x.country===c);const terms=[...new Set(trend.map(x=>x.term))].slice(0,6);
 const trendDays=[...new Set(trend.map(x=>x.date))].sort();
 set('trends-meta',trend.length+'개 확인 · '+(d.api_mode==='free_api_sh'?'무료 API/CSV':'공식 CSV')+(terms.length?' · '+terms.length+'개 검색어':''));
 if(trendDays.length)chart('chart-trends',trendDays,terms.map((term,i)=>({label:term,values:trendDays.map(day=>trend.find(z=>z.date===day&&z.term===term)?.index??null),color:[C.teal,C.navy,C.orange,C.purple,C.grey,C.red][i%6]})),{decimals:1,legend:true,yOptions:{min:0,max:100}});
 else chart('chart-trends',[],[]);
 $('trends-empty').textContent=trendDays.length?'각 CSV의 재정규화 기준이 같을 때만 비교할 수 있습니다.':missing+' 검색어별 관심도는 공식 트렌드 페이지에서 확인하세요.';
 $('trends-link').href=trendsURL(c);
 const ret=(d.retailers||[]).slice().sort((a,b)=>(b.country===c?1:0)-(a.country===c?1:0));
 $('retailer-grid').innerHTML=ret.map(x=>{const arr=(d.retail||[]).filter(z=>z.retailer===x.id||z.retailer===x.name);const last=arr.sort((a,b)=>a.date.localeCompare(b.date)).at(-1);
 return `<div class="retailer"><small>${escapeHtml(x.country)} / RETAIL</small><b>${escapeHtml(x.name)}</b><p>${last?'마지막 관찰 '+escapeHtml(last.date):'실제 판매·리뷰 수 미수집'}</p><a href="${validLink(x.url)}" target="_blank" rel="noopener noreferrer">공식 판매처 보기 ↗</a></div>`}).join('');
 $('demand-sources').innerHTML=[['Amazon BSR',(d.amazon||[]).filter(x=>x.country===c).length+'개 확인값 / '+(d.watchlist||[]).length+'개 ASIN 등록'],['Beauty 상위 목록', rankSnapshots().filter(x=>x.country===c).length+'일 관측 · 부분 목록은 최소 확인 수만 집계'],['Scrape.do',d.scrapedo_reserved_credits!=null?'월 '+d.scrapedo_reserved_credits+'/900 크레딧 보수적 예약 · 비용 헤더 검증 기준':'무료 토큰 미등록 또는 미수집'],['Google Trends',trend.length+'개 값 · '+(d.api_mode==='free_api_sh'?'무료 API.SH': 'CSV 직접 가져오기')],['리테일', (d.retail||[]).length+'개 출처 포함 수동 관찰'],['자동화 상태',d.api_mode==='free_api_sh'?'월 최대 750크레딧 사용 한도 · 초과 전 자동 중단':'무료 키 미설정: Amazon·Trends는 기존 값/CSV']] .map(([a,b])=>`<div class="source-state"><span>${escapeHtml(a)}</span><b>${escapeHtml(b)}</b></div>`).join('');
 renderTop100();
 renderRetailReferences();
}
function renderTop100(){
 const d=state.demand||{}, c=state.country;
 const market=countryMarkets().find(x=>x.code===c);
 const obs=rankSnapshots().filter(x=>x.country===c).slice().sort((a,b)=>a.date.localeCompare(b.date));
 const url=market?.amazon?'https://www.'+market.amazon+'/gp/bestsellers/'+encodeURIComponent(market.amazon_beauty_slug||'beauty')+'/':trendsURL(c);
 $('top100-url').href=url;
 $('top100-url').textContent=market?.amazon?'해당 국가 Amazon Beauty Best Sellers ↗':'독립 아마존 마켓 없음 · Google Trends 보기 ↗';
 const weekly=(state.reference?.amazon_weekly||[]).filter(x=>x.country===c).sort((a,b)=>String(a.date).localeCompare(String(b.date))).at(-1);
 const monthly=(state.reference?.amazon_monthly||[]).filter(x=>x.country===c).sort((a,b)=>String(a.month).localeCompare(String(b.month))).at(-1);
 const extEl=$('top100-external-summary');
 if(extEl){
  const notes=[];
  if(monthly)notes.push('<div><small>독립 월간 순위 조사 · '+escapeHtml(monthly.month)+'</small><strong>해당 월 진입 메디큐브 '+fmt(monthly.medicube_unique_products_seen)+'종</strong><p>'+escapeHtml(monthly.caveat||'월간 관측으로, 특정 하루의 순위와 비교 불가')+'</p><a href="'+validLink(monthly.source_url)+'" target="_blank" rel="noopener noreferrer">영국 공개 조사 원문 ↗</a></div>');
  if(weekly)notes.push('<div><small>제3자 미국 주간 Top100 조사 · '+escapeHtml(weekly.week||'')+'</small><strong>메디큐브 '+escapeHtml(weekly.count)+'개 / 100개</strong><p>다른 관측일·집계방식의 참고자료이며 API 순위와 합산하지 않습니다.</p><a href="'+validLink(weekly.source_url)+'" target="_blank" rel="noopener noreferrer">주간 자료 원문 ↗</a></div>');
  extEl.innerHTML=notes.join('');
 }

 if(!obs.length){
   chart('chart-top100',[],[]);
   set('top100-date','미집계');set('top100-count','—');
   set('top100-coverage',market?.amazon?'최초 API 조회 전':'해당 국가 마켓 없음');
   set('top100-quality',market?.amazon?'아마존 베스트셀러 순위 미수집':'아마존 집계 대상 아님');
   set('top100-entries','데이터가 생기면 동일한 관측 범위의 신규 진입·이탈을 기록합니다.');
   $('top100-items').innerHTML='<div class="blankmini">확인되지 않은 품목 수는 0으로 표시하지 않습니다.</div>';
   return;
 }
 const last=obs[obs.length-1], coverage=Number(last.coverage_count)||0;
 const confirmed=Number(last.medicube_confirmed_count)||0;
 chart('chart-top100',obs.map(x=>x.date.slice(5)),[
   {label:'메디큐브 확인 ASIN 수',values:obs.map(x=>x.medicube_confirmed_count??null),color:C.teal,width:2.6},
   {label:'확보된 Beauty 순위 항목 수',values:obs.map(x=>x.coverage_count??null),color:C.grey,width:1.4,axis:'y1',dash:[4,3]}
 ],{y1:true,legend:true,decimals:0,yOptions:{min:0},xticks:6});
 set('top100-date',last.date);
 set('top100-count',last.coverage_complete?confirmed+'개 (Top 100 확정)':confirmed>0?'최소 '+confirmed+'개':'진입 여부 미확인');
 const observedRanks=(last.rank_coverage||[]).map(Number).filter(Number.isFinite).sort((a,b)=>a-b);
 const observedGroups=[];let groupStart=null,groupEnd=null;
 for(const rank of observedRanks){
   if(groupStart===null){groupStart=rank;groupEnd=rank;}
   else if(rank===groupEnd+1){groupEnd=rank;}
   else{observedGroups.push(groupStart===groupEnd?String(groupStart):groupStart+'~'+groupEnd);groupStart=rank;groupEnd=rank;}
 }
 if(groupStart!==null)observedGroups.push(groupStart===groupEnd?String(groupStart):groupStart+'~'+groupEnd);
 set('top100-coverage','확인 '+coverage+'/100개 순위'+(observedGroups.length?' · '+observedGroups.join(', '):''));
 set('top100-quality',last.coverage_complete?'1~100위 순위 및 100개 상품의 브랜드 확인':last.rank_coverage_complete?'1~100위 순위는 확보했지만 상품명 미확인이 '+(last.unidentified_count??'?')+'개 · 최소 확인 수':'순위 일부만 확인 · 전체 Top 100 품목 수 미확정');
 set('top100-entries',last.new_count!=null&&last.exit_count!=null?
   '관측 범위 내 신규 진입 '+last.new_count+'개 · 이탈 '+last.exit_count+'개':
   '이전 관측과 비교할 동일 범위의 전체 목록이 없어 진입·이탈 집계 보류');
 $('top100-items').innerHTML=(last.medicube_listings||[]).length?
   last.medicube_listings.slice(0,22).map(x=>'<a href="'+validLink(x.url)+'" target="_blank" rel="noopener noreferrer"><b class="rank-num">#'+fmt(x.rank)+'</b><span class="item-title">'+escapeHtml(x.title||x.asin)+'<small> · '+escapeHtml(x.asin)+'</small></span></a>').join(''):
   '<div class="blankmini">'+(last.coverage_complete?'해당 날짜 Beauty Top 100에는 메디큐브 상품이 확인되지 않았습니다.':'현재 확인된 순위 범위에서는 메디큐브 상품이 나타나지 않았습니다. 전체 Top 100에는 있을 수 있습니다.')+'</div>';
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
   const metric=x.display||((x.value??'')+'');
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
 set('kbty-status',e.status||'상태 미확인');set('e-price',e.latest_price_usd!=null?'$'+fmt(e.latest_price_usd,2):'—');set('e-price-date',e.price_date||'거래 전 또는 시세 미확인');
 set('e-aum',e.aum_usd!=null?'$'+fmt(e.aum_usd,0):'—');set('e-apr',e.apr_weight_pct!=null?fmt(e.apr_weight_pct,2)+'%':'—');
 set('e-apr-date',e.apr_holding_as_of||'공식 APR 편입비중 미발표');set('e-shares',e.apr_shares!=null?fmt(e.apr_shares):'—');
 const price=(e.price_history||[]).filter(x=>x.close_usd!=null);chart('chart-etf',price.map(x=>x.date),[{label:'KBTY USD',values:price.map(x=>x.close_usd),color:C.navy}],{decimals:2});
 $('etf-price-empty').textContent=price.length?'':missing+' 공식 상장 후 확인합니다.';
 const au=(e.aum_history||[]).filter(x=>x.aum_usd!=null);chart('chart-aum',au.map(x=>x.date),[{label:'AUM ($)',values:au.map(x=>x.aum_usd),color:C.teal}],{decimals:0});
 $('etf-aum-empty').textContent=au.length?'':missing+' 실제 운용사 AUM 발표가 필요합니다.';
 const holdings=(e.holdings||[]).sort((a,b)=>b.weight_pct-a.weight_pct);
 $('etf-holdings').innerHTML=holdings.length?holdings.slice(0,12).map(x=>`<div class="holding"><span>${escapeHtml(x.name||x.ticker)}</span><b>${fmt(x.weight_pct,2)}%</b></div>`).join(''):
  '<div class="blankmini">상장 후 운용사의 실제 보유종목·비중이 공개되면 표시합니다. 공개 전 0%로 표시하지 않습니다.</div>';
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
function renderLogistics(){
 const data=[{name:'북미',q2:3763,q3:3556,of2:22,of3:30},{name:'유럽',q2:1451,q3:1778,of2:50,of3:40},{name:'아시아',q2:1211,q3:1160},{name:'기타 해외',q2:617,q3:735},{name:'한국',q2:633,q3:502}];
 chart('chart-region',data.map(x=>x.name),[{label:'2026 2Q',values:data.map(x=>x.q2),color:C.navy,background:'#193a5a'},
 {label:'2026 3Q',values:data.map(x=>x.q3),color:C.teal,background:'#0b917f'}],{type:'bar',legend:true});
 $('offline-table').innerHTML=`<table><thead><tr><th>지역</th><th>2Q</th><th>3Q</th><th>매출 QoQ</th></tr></thead><tbody>${data.slice(0,2).map(x=>`<tr><td>${escapeHtml(x.name)}</td><td>${x.of2===22?'약 20~23':x.of2}%</td><td>${x.of3}%</td><td>${signed(pct(x.q3,x.q2))}</td></tr>`).join('')}</tbody></table>`;
 const log=state.market?.logistics||{};
 const sea=(log.sea||[]).slice().sort((a,b)=>String(a.month).localeCompare(String(b.month)));
 const lastSea=sea.at(-1);
 const asof=$('freight-asof');
 if(asof){
   const last=lastSea?.month||'미수집';
   const source=log.source||'관세청 해상수출 운송비용';
   const message=(log.last_fetch_failed?' · 최근 갱신 실패, 마지막 관측 유지':'');
   asof.textContent='공식 통계 기준 '+last+' · 단위: 천원/2TEU (40피트 컨테이너) · '+source+
    ' · 매월 다음 달 중순 발표되는 후행지표'+message;
 }
 const sourceLink=$('freight-source-url');
 if(sourceLink){
   sourceLink.href=validLink(log.source_url||'https://www.customs.go.kr/kcs/na/ntt/selectNttList.do?bbsId=1362&mi=2891');
 }
 chart('chart-sea',sea.map(x=>x.month),[
  {label:'미국 서안',values:sea.map(x=>x.us_west),color:C.navy},{label:'미국 동안',values:sea.map(x=>x.us_east),color:C.teal},
  {label:'유럽',values:sea.map(x=>x.eu),color:C.purple}],{decimals:0,legend:true});
 const errs=state.status?.errors||[];
 set('diagnostic-date',state.status?.generated_at_utc||'최초 데이터 수집 전');
 $('diagnostic-errors').innerHTML=errs.length?errs.slice(0,12).map(x=>`<div class="check"><span class="check-icon caution">!</span><div><b>데이터 접근 또는 출처 확인</b><p>${escapeHtml(x)}</p></div></div>`).join(''):'<div class="check"><span class="check-icon positive">✓</span><div><b>저장된 자료의 필수 오류 미발견</b><p>각 자료의 기준일이 최신인지 별도로 확인하세요.</p></div></div>';
}
function fillProductChoices(){
 const observed=rankSnapshots().filter(s=>s.country===state.country).flatMap(s=>s.medicube_listings||[]);
 const names=new Map();for(const x of observed)names.set(x.asin,x.title||x.asin);
 for(const x of (state.demand?.amazon||[]).filter(z=>z.country===state.country))if(x.asin&&!names.has(x.asin))names.set(x.asin,x.product||x.asin);
 const sel=$('product');if(!sel)return;
 sel.innerHTML='<option value="all">전체 메디큐브 상품</option>'+[...names].map(([asin,name])=>'<option value="'+escapeHtml(asin)+'">'+escapeHtml(name.slice(0,55))+'</option>').join('');
 if(state.product!=='all'&&!names.has(state.product))state.product='all';sel.value=state.product;
}
function initControls(){
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
 const view=$('technical-view');if(view)view.addEventListener('change',()=>{state.techView=view.value;renderTechnical();});
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
 const names=['market','technical','kbty','news','demand','status','top100','reference_signals','kbty_sec','financials','trend_signals','apr_theses','dart_ownership','dart_financials','dart_capital'];const data=await Promise.all(names.map(getJSON));names.forEach((n,i)=>state[n==='reference_signals'?'reference':n==='kbty_sec'?'kbtySec':n==='trend_signals'?'trendSignals':n==='apr_theses'?'aprTheses':n==='dart_ownership'?'dartOwnership':n==='dart_financials'?'dartFinancials':n==='dart_capital'?'dartCapital':n]=data[i]);
 const sync=state.status?.generated_at_utc;
 set('last-synced',sync?'최종 수집 '+sync.slice(0,10)+' (UTC)':'최초 클라우드 갱신 전');
 initControls();showPage(location.hash);window.addEventListener('hashchange',()=>showPage(location.hash));
}
window.addEventListener('DOMContentLoaded',init);
})();
