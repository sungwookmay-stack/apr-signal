/* APR SIGNAL • Free, static, sourced market monitor. No trading order function. */
(()=>{'use strict';
const $=id=>document.getElementById(id);
const fmt=(n,d=0)=>n==null||!Number.isFinite(Number(n))?'—':Number(n).toLocaleString('ko-KR',{minimumFractionDigits:d,maximumFractionDigits:d});
const pct=(a,b)=>a!=null&&b!=null&&Number(b)!==0?(a/b-1)*100:null;
const signed=(n,d=1)=>n==null?'—':(n>0?'+':'')+fmt(n,d)+'%';
const state={market:null,tech:null,kbty:null,news:null,demand:null,status:null,period:'all',country:'US',product:'medicube PDRN pink peptide serum',nav:'overview',charts:{}};
const C={navy:'#193a5a',teal:'#0b917f',orange:'#bf8854',purple:'#8c83b4',grey:'#98aab8',red:'#c35f58'};
const missing='실측 데이터 없음 · 확인된 값만 표시합니다.';
function set(id,val){const e=$(id);if(e)e.textContent=val;}
function safeText(s){return String(s??'');}
function escapeHtml(s){return safeText(s).replace(/[&<>"']/g,m=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));}
function validLink(url){try{let u=new URL(url);return ['https:','http:'].includes(u.protocol)?u.href:'#'}catch{return '#'}}
async function getJSON(name){try{const r=await fetch('./data/'+name+'.json?v='+Date.now(),{cache:'no-store'});if(r.ok)return await r.json()}catch{}return window.APR_BOOTSTRAP?.[name]??null}
function today(){return new Date().toISOString().slice(0,10)}
function showPage(hash){const id=(hash||location.hash||'#overview').replace('#','');state.nav=['overview','technical','demand','kbty','business','logistics'].includes(id)?id:'overview';document.querySelectorAll('[data-page]').forEach(x=>x.classList.toggle('active',x.dataset.page===state.nav));document.querySelectorAll('[data-nav]').forEach(x=>x.classList.toggle('active',x.dataset.nav===state.nav));document.querySelectorAll('[data-mnav]').forEach(x=>x.classList.toggle('active',x.dataset.mnav===state.nav));if(state.nav==='technical')renderTechnical();if(state.nav==='demand')renderDemand();if(state.nav==='kbty')renderEtf();if(state.nav==='business')renderNews();if(state.nav==='logistics')renderLogistics();if(state.nav==='overview')renderOverview();window.scrollTo({top:0,behavior:'instant'});}
function marketRows(){return (state.market?.series||[]).filter(x=>x.date>='2026-05-01'&&x.close_krw).sort((a,b)=>a.date.localeCompare(b.date));}
function dateLimit(rows){const n=Number(state.period);return Number.isFinite(n)&&n>0?rows.filter(x=>x.date>=new Date(Date.now()-n*86400000).toISOString().slice(0,10)):rows;}
function chart(id,labels,series,extra={}){
 const el=$(id);if(!el)return;
 const prev=state.charts[id];if(prev){prev.destroy();delete state.charts[id]}
 if(typeof Chart==='undefined'){const alt=$(id.replace('chart-','fallback-'));if(alt)alt.hidden=false;el.style.display='none';return}
 el.style.display='block';
 const datasets=series.map((x,i)=>({
    label:x.label||'—',data:x.values||[],borderColor:x.color||Object.values(C)[i%5],
    backgroundColor:x.background||'transparent',borderWidth:x.width??2,
    pointRadius:0,pointHoverRadius:3,tension:extra.smooth??0.15,
    spanGaps:false,fill:x.fill??false,yAxisID:x.axis||'y',borderDash:x.dash||[],
    ...(extra.datasetOverrides||{})
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
 return `<tr><td>${escapeHtml(mon)}</td><td>${p?'₩'+fmt(p.close_krw):'—'}</td><td>${p&&p.close_usd!=null?'$'+fmt(p.close_usd,2):'—'}</td><td>${fmt(avg(o.fxusd),1)}</td><td>${fmt(avg(o.fxeur),1)}</td></tr>`}).join('');
}
function renderTechnical(){const d=state.tech,last=d?.last;
 if(!last||!last.date){set('t-decision','분석 자료 미확보');set('t-add','보류');return}
 set('t-decision',last.label||'—');set('t-date','분석일 '+last.date);set('t-score',last.score!=null?(last.score>0?'+':'')+last.score:'—');
 set('t-add',last.averaging_down||'미확인');set('t-risk-message',last.add_criteria||'구름 및 볼린저 반등 확인 필요');
 set('t-risk-price',last.risk_reference!=null?'₩'+fmt(last.risk_reference):'—');
 const checks=last.checks||[];
 $('technical-checks').innerHTML=checks.length?checks.map(x=>`<div class="check"><span class="check-icon ${escapeHtml(x.status)}">${x.status==='positive'?'✓':x.status==='negative'?'×':'?'}</span><div><b>${escapeHtml(x.name)}</b><p>${escapeHtml(x.detail||({positive:'상승 방향',negative:'약세 방향',unknown:'데이터 부족',caution:'주의'}[x.status]||''))}</p></div></div>`).join(''):`<div class="blankmini">${missing}</div>`;
 const arr=(d.series||[]).filter(x=>x.date>='2026-05-01').slice(-90);
 const lines=[['close','종가',C.navy,2.6],['bb_upper','BB 상단',C.teal,1.5],['bb_lower','BB 하단',C.teal,1.5],['tenkan','전환선',C.orange,1.4],['kijun','기준선','#d9aa65',1.4],['cloud_a','구름 A','#7b7aa6',1.3],['cloud_b','구름 B','#a5a3c7',1.3]];
 chart('chart-technical',arr.map(x=>x.date.slice(5)),lines.map(([key,label,color,w])=>({label,values:arr.map(x=>x[key]),color,width:w,dash:['cloud_a','cloud_b'].includes(key)?[4,3]:[]})),{yformat:'k',decimals:0,legend:false,xticks:7});
 chart('chart-rsi',arr.map(x=>x.date.slice(5)),[{label:'RSI(14)',color:C.orange,values:arr.map(x=>x.rsi14)}],{decimals:1,yOptions:{min:0,max:100},xticks:6});
 const t=arr.at(-1);if(t){$('t-short-metrics').innerHTML=[['RSI(14)',t.rsi14!=null?fmt(t.rsi14,1):null],['MACD',t.macd!=null?fmt(t.macd,1):null],['MACD 히스토그램',t.macd_hist!=null?fmt(t.macd_hist,1):null],['BB 하단',t.bb_lower!=null?'₩'+fmt(t.bb_lower):null],['BB 상단',t.bb_upper!=null?'₩'+fmt(t.bb_upper):null],['ATR(14)',t.atr14!=null?'₩'+fmt(t.atr14):null]].map(([a,b])=>`<span>${escapeHtml(a)} <strong>${escapeHtml(b||'—')}</strong></span>`).join('')}
}
function trendsURL(country){const words=state.demand?.trends_terms||{};let terms=country==='CL'?words.CL: ['AE','SA','EG','QA','KW'].includes(country)?words.ME:words.default;
 const q=(terms||['medicube']).slice(0,5).join(',');return 'https://trends.google.com/trends/explore?date='+encodeURIComponent('2026-05-01 '+today())+'&geo='+encodeURIComponent(country)+'&q='+encodeURIComponent(q);
}
function renderDemand(){const d=state.demand;if(!d)return;
 const c=state.country,p=state.product,market=(d.countries||[]).find(x=>x.code===c);
 const list=(d.amazon||[]).filter(x=>x.country===c&&(!p||x.product===p));list.sort((a,b)=>a.date.localeCompare(b.date));
 set('amazon-meta',list.length+'건 · 데이터 출처별 검증 필요');
 if(list.length){const dates=[...new Set(list.map(x=>x.date))].sort();const asins=[...new Set(list.map(x=>x.asin))];chart('chart-amazon',dates,asins.slice(0,6).map((asin,i)=>({label:asin,values:dates.map(day=>list.find(x=>x.date===day&&x.asin===asin)?.bsr??null),color:[C.teal,C.navy,C.orange,C.purple,C.grey,C.red][i%6]})),{yOptions:{reverse:true},legend:asins.length>1});}
 else chart('chart-amazon',[],[]);
 $('amazon-empty').textContent=list.length?'카테고리가 다른 순위는 직접 비교할 수 없습니다.':missing+' 공식 판매순위는 아마존 페이지에서 확인할 수 있습니다.';
 if(market&&market.amazon)$('amazon-link').href='https://www.'+market.amazon+'/s?k='+encodeURIComponent(p||'medicube');else $('amazon-link').href='https://trends.google.com/trends/explore';
 $('amazon-link').textContent=market?.amazon?'현지 아마존에서 제품 검색 ↗':'아마존 독립 마켓플레이스 없음';
 const trend=(d.trends||[]).filter(x=>x.country===c);const terms=[...new Set(trend.map(x=>x.term))].slice(0,6);
 const days=[...new Set(trend.map(x=>x.date))].sort();
 set('trends-meta',trend.length+'개 확인 · '+(d.api_mode==='free_api_sh'?'무료 API/CSV':'공식 CSV')+(terms.length?' · '+terms.length+'개 검색어':''));
 if(days.length)chart('chart-trends',days,terms.map((term,i)=>({label:term,values:days.map(day=>trend.find(z=>z.date===day&&z.term===term)?.index??null),color:[C.teal,C.navy,C.orange,C.purple,C.grey,C.red][i%6]})),{decimals:1,legend:true,yOptions:{min:0,max:100}});
 else chart('chart-trends',[],[]);
 $('trends-empty').textContent=days.length?'각 CSV의 재정규화 기준이 같을 때만 비교할 수 있습니다.':missing+' 검색어별 관심도는 공식 트렌드 페이지에서 확인하세요.';
 $('trends-link').href=trendsURL(c);
 const ret=(d.retailers||[]);
 $('retailer-grid').innerHTML=ret.map(x=>{const arr=(d.retail||[]).filter(z=>z.retailer===x.id||z.retailer===x.name);const last=arr.sort((a,b)=>a.date.localeCompare(b.date)).at(-1);
 return `<div class="retailer"><small>${escapeHtml(x.country)} / RETAIL</small><b>${escapeHtml(x.name)}</b><p>${last?'마지막 관찰 '+escapeHtml(last.date):'실제 판매·리뷰 수 미수집'}</p><a href="${validLink(x.url)}" target="_blank" rel="noopener noreferrer">공식 판매처 보기 ↗</a></div>`}).join('');
 $('demand-sources').innerHTML=[['Amazon BSR',list.length+'개 확인값 / '+(d.watchlist||[]).length+'개 ASIN 등록'],['Google Trends',trend.length+'개 값 · '+(d.api_mode==='free_api_sh'?'무료 API.SH': 'CSV 직접 가져오기')],['리테일', (d.retail||[]).length+'개 출처 포함 수동 관찰'],['자동화 상태',d.api_mode==='free_api_sh'?'월 최대 750크레딧 사용 한도 · 초과 전 자동 중단':'무료 키 미설정: Amazon·Trends는 기존 값/CSV']] .map(([a,b])=>`<div class="source-state"><span>${escapeHtml(a)}</span><b>${escapeHtml(b)}</b></div>`).join('');
}
function renderEtf(){const e=state.kbty;if(!e)return;
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
function renderNews(){const d=state.news;if(!d)return;
 const events=(d.verified_events||[]).slice().sort((a,b)=>b.date.localeCompare(a.date));
 $('verified-events').innerHTML=events.map(x=>`<article class="event"><span class="tag">${escapeHtml(x.date)} · ${escapeHtml(x.country)} · ${escapeHtml(x.stage)}</span><h3>${escapeHtml(x.title)}</h3><p>${escapeHtml(x.summary||'')}</p><a href="${validLink(x.source_url)}" target="_blank" rel="noopener noreferrer">원문 확인 ↗</a></article>`).join('');
 const word=$('news-filter')?.value||'all';const items=(d.items||[]).filter(x=>word==='all'||(x.category||'').includes(word));
 $('news-stack').innerHTML=items.length?items.slice(0,36).map(x=>`<a class="news-card" href="${validLink(x.url)}" target="_blank" rel="noopener noreferrer"><small>${escapeHtml(x.published||'날짜 미확인')} · ${escapeHtml(x.country||'')} · ${escapeHtml(x.category||'')}</small><strong>${escapeHtml(x.title)}</strong><span class="news-status">관련 기사 · 실제 발주·매출·허가는 별도 확인 필요 ↗</span></a>`).join(''):
  '<div class="panel padded" style="grid-column:1/-1"><p class="subtle">현재 저장된 RSS 기사 실측이 없습니다. 자동 갱신이 성공하면 날짜별로 여기에 누적됩니다.</p><a class="minor-button" href="https://news.google.com/search?q=medicube%20Chile%20Kinegun&hl=es-419&gl=CL&ceid=CL%3Aes-419" target="_blank" rel="noopener">칠레 스페인어 뉴스 직접 검색 ↗</a></div>';
}
function renderLogistics(){
 const data=[{name:'북미',q2:3763,q3:3556,of2:22,of3:30},{name:'유럽',q2:1451,q3:1778,of2:50,of3:40},{name:'아시아',q2:1211,q3:1160},{name:'기타 해외',q2:617,q3:735},{name:'한국',q2:633,q3:502}];
 chart('chart-region',data.map(x=>x.name),[{label:'2026 2Q',values:data.map(x=>x.q2),color:C.navy,background:'#193a5a'},
 {label:'2026 3Q',values:data.map(x=>x.q3),color:C.teal,background:'#0b917f'}],{type:'bar',legend:true});
 $('offline-table').innerHTML=`<table><thead><tr><th>지역</th><th>2Q</th><th>3Q</th><th>매출 QoQ</th></tr></thead><tbody>${data.slice(0,2).map(x=>`<tr><td>${escapeHtml(x.name)}</td><td>${x.of2===22?'약 20~23':x.of2}%</td><td>${x.of3}%</td><td>${signed(pct(x.q3,x.q2))}</td></tr>`).join('')}</tbody></table>`;
 const sea=(state.market?.logistics?.sea||[]);chart('chart-sea',sea.map(x=>x.month),[
  {label:'미국 서안',values:sea.map(x=>x.us_west),color:C.navy},{label:'미국 동안',values:sea.map(x=>x.us_east),color:C.teal},
  {label:'유럽',values:sea.map(x=>x.eu),color:C.purple}],{decimals:0,legend:true});
 const errs=state.status?.errors||[];
 set('diagnostic-date',state.status?.generated_at_utc||'최초 데이터 수집 전');
 $('diagnostic-errors').innerHTML=errs.length?errs.slice(0,12).map(x=>`<div class="check"><span class="check-icon caution">!</span><div><b>데이터 접근 또는 출처 확인</b><p>${escapeHtml(x)}</p></div></div>`).join(''):'<div class="check"><span class="check-icon positive">✓</span><div><b>저장된 자료의 필수 오류 미발견</b><p>각 자료의 기준일이 최신인지 별도로 확인하세요.</p></div></div>';
}
function initControls(){
 const d=state.demand||{};const country=$('country');country.innerHTML=(d.countries||[]).map(x=>`<option value="${escapeHtml(x.code)}">${escapeHtml(x.region)} · ${escapeHtml(x.name)}</option>`).join('');
 country.value=state.country;country.addEventListener('change',()=>{state.country=country.value;renderDemand()});
 const product=$('product');product.innerHTML=(d.products||[]).map(x=>`<option value="${escapeHtml(x)}">${escapeHtml(x)}</option>`).join('');
 product.value=state.product;product.addEventListener('change',()=>{state.product=product.value;renderDemand()});
 $('period').addEventListener('change',e=>{state.period=e.target.value;renderOverview()});
 $('news-filter').addEventListener('change',renderNews);
 $('download-market').addEventListener('click',()=>{
  const rows=marketRows();if(!rows.length)return alert('내려받을 실제 시세 데이터가 없습니다.');
  const cols=['date','open_krw','high_krw','low_krw','close_krw','close_usd','usdkrw','eurkrw','volume'];
  const csv=[cols.join(','),...rows.map(x=>cols.map(c=>x[c]??'').join(','))].join('\n');
  const blob=new Blob(['\uFEFF',csv],{type:'text/csv;charset=utf-8'});const u=URL.createObjectURL(blob);const a=document.createElement('a');a.href=u;a.download='APR_278470_KRW_USD_2026-05.csv';a.click();setTimeout(()=>URL.revokeObjectURL(u),2000);
 });
}
async function init(){
 const names=['market','technical','kbty','news','demand','status'];const data=await Promise.all(names.map(getJSON));names.forEach((n,i)=>state[n]=data[i]);
 const sync=state.status?.generated_at_utc;
 set('last-synced',sync?'최종 수집 '+sync.slice(0,10)+' (UTC)':'최초 클라우드 갱신 전');
 initControls();showPage(location.hash);window.addEventListener('hashchange',()=>showPage(location.hash));
}
window.addEventListener('DOMContentLoaded',init);
})();
