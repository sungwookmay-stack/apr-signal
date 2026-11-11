/* Official-registry observations only. No key or live API call in the browser. */
(function () {
  'use strict';
  const labels = {
    not_configured: 'API 연결 전 · 인허가 실측 미확인',
    authorization_denied: 'API 이용권한 확인 필요 · 이전 성공 자료만 유지',
    network_error: '최신 조회 실패 · 이전 성공 자료만 유지',
    http_error: '최신 조회 실패 · 이전 성공 자료만 유지',
    fetch_failed: '저장 데이터 로딩 실패 · 현재 상태 미확인',
    ok: '공식 등록부 전체조회 완료 · 국내 판매 범위 별도 확인'
  };
  function esc(value) {
    return String(value == null || value === '' ? '—' : value).replace(/[&<>"']/g,
      c => ({'&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;'}[c]));
  }
  function date(value) {
    const s = String(value || '');
    if (/^\d{8}$/.test(s)) return `${s.slice(0,4)}-${s.slice(4,6)}-${s.slice(6,8)}`;
    return s || '미확인';
  }
  function text(id, value) {
    const node = document.getElementById(id); if (node) node.textContent = value;
  }
  function html(id, value) {
    const node = document.getElementById(id); if (node) node.innerHTML = value;
  }
  function render(data) {
    data = data && typeof data === 'object' ? data : {};
    const complete = data.status === 'ok' && data.current_scan_complete === true;
    text('mfds-status', labels[data.status] || '조회 불완전 · 이전 성공 자료만 유지');
    text('mfds-dates', `최근 실행: ${date(data.checked_at)} · 마지막 전체조회 성공: ${date(data.last_success_at)}`);
    text('mfds-count', complete && Number.isInteger(data.observed_count)
      ? `이번 조회 ${data.observed_count}개 등록정보 관측 (APR 관련 후보 포함)`
      : '현재 관측 건수 미확인');
    text('mfds-caution', complete
      ? '등록정보 발견은 국내 신규 승인·판매 개시를 의미하지 않습니다. 수출전용 여부와 허가·인증·신고 범위를 원문에서 확인해야 합니다.'
      : '연결 전이거나 조회가 불완전합니다. 빈 목록은 미허가·신청 반려를 의미하지 않으며, 과거 성공 자료가 있으면 그 기록만 표시합니다.');
    const records = Array.isArray(data.records) ? data.records : [];
    html('mfds-records', records.length ? records.map(r => {
      const match = r.company_match === 'public_business_number' ? 'APR 공개 사업자번호 일치'
        : r.company_match === 'exact_company_name_requires_initial_identity_review' ? '업체명 일치 · 최초 법인 대조 필요'
        : '관련성 후보 · 법인 대조 필요';
      const presence = r.presence === 'observed' ? (complete ? '이번 조회 관측' : '과거 조회 관측')
        : '이번 전체조회 미관측 · 취소 단정 불가';
      return `<tr><td>${esc(r.company)}<br><small>${esc(match)}</small></td>` +
        `<td>${esc(r.product)}<br><small>모델 ${esc(r.model)}</small></td>` +
        `<td>${esc(r.permit_number)}<br><small>등급 ${esc(r.grade)} · 분류 ${esc(r.classification)}</small></td>` +
        `<td>허가일 ${esc(date(r.permit_date))}<br>변경일 ${esc(date(r.registry_changed_at))}` +
        `<br><small>최초 관측 ${esc(date(r.first_seen_at))}</small></td>` +
        `<td>${esc(presence)}<br>취소취하 코드 ${esc(r.cancellation_code_raw)}` +
        `<br><small>취소취하 일시 ${esc(r.cancellation_at_raw)} · 코드 원문</small></td>` +
        `<td>국내 판매 범위 미검증<br><small>수출전용 여부 원문 대조 필요</small>` +
        `<details><summary>등록 사용목적</summary><p>${esc(r.permitted_use)}</p></details></td></tr>`;
    }).join('') : '<tr><td colspan="6">확인된 등록정보가 아직 없습니다. 미허가 판정이 아닙니다.</td></tr>');
    const events = Array.isArray(data.event_history) ? data.event_history.slice(-10).reverse() : [];
    const names = {newly_observed_registry_record: '등록정보 새로 발견 (신규 승인 아님)',
      registry_record_changed: '등록정보 변경', not_observed_requires_review: '전체조회에서 미관측 (취소 판정 아님)'};
    html('mfds-events', events.length ? '<ul>' + events.map(e =>
      `<li>${esc(date(e.at))} · ${esc(names[e.kind] || '원문 재확인 필요')} · ${esc(e.record_key)}</li>`).join('') + '</ul>'
      : '<p class="under-note">확인된 변경 이력 없음. 최초 성공 조회는 기준 목록만 만들며 과거 품목을 신규 허가로 알리지 않습니다.</p>');
  }
  async function load() {
    if (!document.getElementById('mfds-status')) return;
    try {
      const response = await fetch('./data/mfds_devices.json', {cache:'no-store'});
      if (!response.ok) throw Error('static_data_unavailable');
      const data = await response.json();
      if (!data || data.schema_version !== 1 || !Array.isArray(data.records)) throw Error('invalid_schema');
      render(data);
    } catch (_) { render({status:'fetch_failed'}); }
  }
  if (typeof module !== 'undefined' && module.exports) module.exports = {render, esc, date};
  if (typeof window !== 'undefined') window.addEventListener('DOMContentLoaded', load);
})();
