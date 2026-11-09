/* APR investor supply/demand monitor, source-aware and gap-aware. */
(() => {'use strict';
const ACTORS=[
  ['foreign','외국인 합계'],['institution','기관 합계'],
  ['pension','연기금 등'],['individual','개인']
];
const LABEL={
  strong:'지속성 확인',positive:'순매수 우위',
  watch:'추가 확인 필요',mixed:'엇갈림',weak:'매도 우위',
  unknown:'판정 보류'
};
let initialized=false,windowDays='20';
const asNum=x=>x!==null&&x!==undefined&&Number.isFinite(Number(x))?Number(x):null;
const won=(v,fmt)=>{
 if(v===null||v===undefined||!Number.isFinite(Number(v)))return '—';
 const v100=Number(v)/1e8;return (v100>0?'+':v100<0?'−':'')+fmt(Math.abs(v100),1)+'억원';
};
const count=(v,fmt)=>v==null?'—':fmt(v)+'주';
function render(ctx){
 const {$,state,fmt,escapeHtml,chart,C,validLink}=ctx;
 const data=state.flows||{},ref=state.flowReference||{};
 const actors=data.actors||{};
 const priceDay=state.market?.meta?.stock_last||state.market?.series?.at(-1)?.date;
 const flowDay=data.flow_last_date;
 const matched=!!flowDay&&flowDay===priceDay;
 const summary=data.combined||{};
 const hasFull20=!!(actors.foreign?.windows?.['20']&&actors.institution?.windows?.['20']);
 const totalReady=matched&&hasFull20;
 const statusNote=(data.data_status?.issues||[]).join(' · ');
 const naverInfo=data.data_status?.naver_public_result||{};
 const naverEstimated=!!data.data_status?.naver_flow_is_estimated;
 const sourceInfo=data.data_status||{};
 const kiwoomInfo=sourceInfo.kiwoom_read_only_result||{};
 const kisInfo=sourceInfo.kis_short_daily_result||{};
 const fscInfo=sourceInfo.fsc_lending_status||'not_configured';
 const kisText='공매도 거래 KIS: '+
   (sourceInfo.kis_short_key_configured?
      (kisInfo.status||'조회 상태 미확인')+
      ' · '+(kisInfo.rows||0)+'거래일':
      'API 키 미연결')+
   ' (순보유잔고는 별도)';
 const kiwoomStatus=sourceInfo.kiwoom_app_configured?
   (kiwoomInfo.status==='disabled_dynamic_runner_ip'?
     '키움 키 보관 중 · GitHub IP 제한으로 호출 생략':
     '키움 REST '+(kiwoomInfo.status||'미확인')+
     (kiwoomInfo.asof?' · 기준일 '+kiwoomInfo.asof:'')):
   '키움 REST 미연결 (선택 사항)';
 const status=$('flow-collection-status');
 if(status)status.textContent='시세 기준 '+(priceDay||'미확인')+
    ' / 투자자별 실측 '+(flowDay||'미수집')+
    ' · '+(matched?'날짜 정합성 충족':'날짜 불일치·자료 부족')+
    ' · 네이버 KRX 공개 데이터 '+(naverInfo.status||'미수집')+
    ' '+(naverInfo.rows||0)+'거래일 · '+kisText+' · '+kiwoomStatus+
    (statusNote?' · '+statusNote:'');
 const title=$('flow-total-label');
 if(title)title.textContent=totalReady?(summary.label||'수급 분석 대기'):
    '종목별 연속 수급 미확인 · 판정 보류';
 const desc=$('flow-total-detail');
 if(desc)desc.textContent=totalReady?(summary.detail||''):
    '기준일이 다른 정보·5/20일 미충족 자료를 합산해 매집 확정으로 표시하지 않습니다.';
 const indicator=state.technical?.bottom;
 $('flow-price-bottom').textContent=indicator?.stage?
    '가격·바닥 판단: '+indicator.stage+' (기준 '+(indicator.date||'미확인')+')':
    '기술적 바닥 판별 자료 미수집';
 const rec=[['5','5거래일'],['20','20거래일'],['60','60거래일']];
 const table=$('flow-summary-body');
 if(table){
   table.innerHTML=ACTORS.map(([key,name])=>{
     const a=actors[key]||{},status=a.windows||{};
     const w=(n)=>status[n]?.net_krw;
     const type=a.level||'unknown';
     return '<tr><td><strong>'+escapeHtml(name)+'</strong><small>'+
         escapeHtml(a.label||'실측 부족')+'</small></td>'+
       rec.map(([n])=>'<td>'+
        (status[n]?.estimated_value_days?'≈':'')+
        won(w(n),fmt)+'</td>').join('')+
       '<td>'+escapeHtml(LABEL[type]||LABEL.unknown)+'</td></tr>';
   }).join('');
 }
 const period=$('flow-period');
 if(period)windowDays=period.value||'20';
 const n=Number(windowDays)||20;
 const prices=(state.market?.series||[]).filter(x=>x?.date).slice(-n);
 const days=prices.map(x=>x.date);
 const byDay=new Map((data.daily||[]).map(x=>[x.date,x]));
 // Net investor trades and net shares/short volume are distinct concepts.
 // Missing date or category is plotted as a gap, not zero.
 const dayFlows=days.map(d=>byDay.get(d)||{});
 const vis=ACTORS.map(([key,label],i)=>{
   let running=0;
   return {label,values:dayFlows.map((r)=>{
       const value=asNum(r[key]);
       if(value===null)return null;
       running+=value/1e8;
       return Math.round(running*10)/10;
   }),color:[C.navy,C.teal,C.purple,C.orange][i]};
 });
 chart('flow-cum-chart',days.map(d=>d.slice(5)),vis,{legend:true,decimals:1,xticks:8,suffix:'억원'});
 const latest=data.latest_daily||{};
 $('flow-latest-daily').textContent=flowDay?
   flowDay+(latest.amount_estimated?
      ' KRX 순매수 주수 × 당일 종가 추정금액 · 외국인 ':
      ' 실제 순매수 거래대금 · 외국인 ')+won(latest.foreign,fmt)+
   ' / 기관 '+won(latest.institution,fmt)+
   ' / 연기금 '+won(latest.pension,fmt)+
   ' / 개인 '+won(latest.individual,fmt):
   '종목별 일간 수급 미수집. 수집된 날짜만 표시하며 데이터 공백은 0으로 채우지 않습니다.';
 const refBox=$('flow-external-reference');
 if(refBox){
   const values=ref.net_by_actor_100m_krw||{};
   refBox.innerHTML=ref?.as_of?
     '<div class="flow-ref-head"><strong>외부 KRX 기반 참고 요약 · '+escapeHtml(ref.as_of)+'</strong>'+
     '<small>2차 집계 · 분석 점수 계산에서 제외</small></div>'+
     '<p class="under-note">5일 합계만 보면 외국인·기관이 매수 우위지만, 20일 합계는 매도 우위로 방향이 달라질 수 있습니다. 동일한 시계열로 확정 확인되기 전에는 ‘좋은 수급’으로 단정하지 않습니다.</p>'+
     '<div class="tablebox"><table><thead><tr><th>투자자</th><th>5거래일</th><th>20거래일</th><th>60거래일</th></tr></thead><tbody>'+
      [['foreign','외국인'],['institution','기관'],['individual','개인']].map(([key,name])=>
        '<tr><td>'+name+'</td>'+['5','20','60'].map(day=>{
            const val=asNum(values[key]?.[day]);
            return '<td>'+(val===null?'—':(val>0?'+':val<0?'−':'')+fmt(Math.abs(val))+'억원')+'</td>';
        }).join('')+'</tr>').join('')+'</tbody></table></div>'+
      '<p class="under-note">원천: <a href="'+validLink(ref.provider_url||'#')+
      '" target="_blank" rel="noopener noreferrer">'+escapeHtml(ref.provider||'2차 자료')+
      ' ↗</a> · '+escapeHtml(ref.market_scope||'시장 범위 확인 전')+
      ' · 일간·연기금 개별 수치는 이 집계에 포함되지 않습니다.</p>':
      '<p class="under-note">독립 검증한 외부 참고 스냅샷이 없습니다.</p>';
 }
 const short=data.short||{}, sh=short.latest||{};
 const qty=sh.reported_net_short_balance_qty;
 const sourceShortVolume=sh.short_volume_ratio_pct!=null;
 const latestShortRatio=sourceShortVolume?sh.short_volume_ratio_pct:sh.short_value_ratio_pct;
 $('flow-short-ratio').textContent=latestShortRatio!=null?
    fmt(latestShortRatio,2)+'%':'—';
 $('flow-short-day').textContent=short.last_date?
    '공매도 거래 기준 '+short.last_date+
    (sourceShortVolume?' · 공매도 주수 / 당일 전체 거래량':
     sh.ratio_estimated_from_close_volume?' · 종가×거래량 대비 금액 근사치':
     ' · 산출 기준 확인 필요'):
    '종목별 공매도 거래 실측 미확인';
 $('flow-short-position').textContent=qty!=null?count(qty,fmt):'—';
 $('flow-short-mean20').textContent=short.short_volume_period20_pct!=null?
     fmt(short.short_volume_period20_pct,2)+'%':'—';
 $('flow-short-position-note').textContent='공매도 순보유잔고: 신고의무 대상자의 보고분. T+2 시차 및 사후 정정 가능. 대차잔고와 다릅니다.';
 const lending=data.lending||{},l=lending.latest||{};
 $('flow-loan-new').textContent=count(l.new_qty,fmt);
 $('flow-loan-return').textContent=count(l.returned_qty,fmt);
 $('flow-loan-bal').textContent=count(l.balance_qty,fmt);
 $('flow-loan-date').textContent=lending.last_date?
   '대차 관측 '+lending.last_date+' · 단위 주':
   '대차 실측 미수집 · 금융위 API '+(
     sourceInfo.fsc_stock_lending_key_configured?'키 등록 확인, 응답 매핑 점검 필요':
     'GitHub FSC_STOCK_LENDING_API_KEY 등록 필요')+
   ' · KSD/API 별도';
 const risk=[];
 if(short.short_ratio_mean20_pct!=null&&short.short_ratio_mean20_pct>=10)
   risk.push('최근 20일 공매도 거래대금 근사 비중 높음(10% 이상)');
 if(lending.balance_change!=null&&lending.balance_change>0)
   risk.push('대차 잔고 증가: 실제 공매도 거래·잔고와 별도 확인');
 if(sh.reported_net_short_balance_qty!=null&&l.balance_qty!=null)
   risk.push('공매도 순보유잔고와 대차잔고를 동일 수치로 합산하지 않음');
 $('flow-risk-note').textContent=risk.length?risk.join(' · '):
   '공매도·대차 데이터가 불충분하면 위험 감소/증가를 임의 판정하지 않습니다.';
 const rows=(data.daily||[]).slice(-20).reverse();
 const tbody=$('flow-daily-body');
 if(tbody)tbody.innerHTML=rows.length?
   rows.map(x=>'<tr><td>'+escapeHtml(x.date||'')+'</td>'+
     ACTORS.map(([key])=>'<td>'+won(x[key],fmt)+'</td>').join('')+'</tr>').join(''):
   '<tr><td colspan="5">검증된 일간 수급 실측 없음. 조회 일자가 확인된 기록만 누적합니다.</td></tr>';
 const histShort=(data.short_daily||[]).slice(-n);
 chart('flow-short-chart',histShort.map(x=>x.date?.slice(5)||''),[
   {label:'공매도 거래비중 (수량 기준 우선)',
    values:histShort.map(x=>x.short_volume_ratio_pct??x.short_value_ratio_pct??null),color:C.red}
 ],{legend:true,decimals:1,suffix:'%'});
 $('flow-policy').textContent=
   (naverEstimated?'≈ 표시: 네이버 공개 KRX 순매수 주수 × KRX 당일 종가로 계산한 참고금액입니다. 실제 체결 순매수 거래대금이 아닙니다. 연기금 개별 데이터도 없습니다. ':'')+
   '판정 기준은 5·20·60일 일별 수급, 매수일 비율, 거래대금 대비 순매수 강도와 주가 동행입니다. '+
   '연기금은 기관 합계에 포함하므로 외국인+기관과 따로 더하지 않습니다. '+
   '시장 범위(KRX/NXT)·확정 시각이 다른 자료는 단순 합산하지 않습니다.';
}
function init(ctx){
 if(initialized)return;
 const sel=ctx.$('flow-period');
 if(sel)sel.addEventListener('change',()=>render(ctx));
 initialized=true;
 render(ctx);
}
window.APR_FLOWS={init,render};
})();