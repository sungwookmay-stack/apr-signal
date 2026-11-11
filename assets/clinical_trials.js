(()=>{
'use strict';
const esc=v=>String(v??'미공개').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const status={RECRUITING:'모집 중',NOT_YET_RECRUITING:'모집 전',ACTIVE_NOT_RECRUITING:'진행 중 · 모집 종료',COMPLETED:'연구 완료',TERMINATED:'조기 종료',WITHDRAWN:'철회',SUSPENDED:'중단',UNKNOWN:'상태 미확인'};
const el=id=>document.getElementById(id);
function render(data){
 const ok=data.status==='ok';
 el('clinical-status').textContent=ok?`공개 연구 ${data.observed_count}건 관측 · 인허가 신청 확인 아님`:'최신 조회 실패 · 이전 관측 자료입니다';
 el('clinical-dates').textContent=`최근 조회: ${data.checked_at||'미확인'} · 마지막 성공: ${data.last_success_at||'없음'} (UTC)`;
 el('clinical-records').innerHTML=(data.records||[]).map(r=>{
 const href=/^NCT\d{8}$/.test(r.nct_id)?`https://clinicaltrials.gov/study/${r.nct_id}`:'https://clinicaltrials.gov/';
 return `<article class="panel padded"><h3><a href="${href}" target="_blank" rel="noopener noreferrer">${esc(r.nct_id)} ↗</a> · ${esc(status[r.status]||r.status)}</h3><p>${esc(r.title)}</p><p>의뢰자: ${esc(r.sponsor)} · 연구 코드: ${esc(r.protocol_id)}</p>${r.nct_id==='NCT07871708'?'<p>가정용 다기능 뷰티기기 사용에 따른 피부 외관·안전성 연구. 상업 제품명·국내 허가 신청은 확인되지 않았습니다.</p>':''}<p>연구 시작: ${esc(r.start?.date)} (${r.start?.type==='ACTUAL'?'실제':'예정/미확인'}) · 예상/실제 참여자: ${esc(r.enrollment?.count)}명 (${r.enrollment?.type==='ACTUAL'?'실제':'예정/미확인'})</p><p>최초 공개: ${esc(r.first_posted)} · 원문 최종 갱신: ${esc(r.updated)} · 종료: ${esc(r.completion?.date)} (${r.completion?.type==='ACTUAL'?'실제':'예정/미확인'})</p><p class="under-note">최초 관측: ${esc(r.first_seen)} · 마지막 관측: ${esc(r.last_seen)} · ${!ok?'과거 조회 자료':r.present?'이번 조회 관측':'이번 검색에서 미관측 · 중단 단정 불가'}</p></article>`;
 }).join('')||'<p>관측 자료 없음 · 연구 부재 또는 신청 반려를 의미하지 않습니다.</p>';
 el('clinical-events').innerHTML=(data.events||[]).slice(-10).reverse().map(e=>`<p>${esc(e.at)} · ${esc(e.nct_id)} · ${e.kind==='first_observed'?'최초 관측 (신규 신청·허가 아님)':'등록정보 변화: '+esc(e.fields.join(', '))}</p>`).join('')||'<p>관측 이력 없음</p>';
}
async function load(){try{const r=await fetch('./data/clinical_trials.json',{cache:'no-store'});if(!r.ok)throw Error();render(await r.json());}catch{render({status:'error'});}}
window.addEventListener('DOMContentLoaded',load);
if(typeof module!=='undefined')module.exports={render,load};
})();
