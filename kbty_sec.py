#!/usr/bin/env python3
"""Free SEC EDGAR KBTY filing monitor: source-verified Korean digest.

KBTY is one series (S000109351) of registrant Guinness Atkinson Funds,
CIK 0000919160. The registrant's EDGAR submissions contain MANY unrelated
funds. This monitor never treats a registrant-level form as a KBTY filing
unless the SEC filing index headers explicitly identify KBTY's series ID.

Reviewed documents in config/kbty_sec_registry.json have researched summaries.
New series-verified forms receive ONLY a form-type explanation (not a claim to
have summarized the entire document). A SEC 403/timeout leaves history intact
with an explicit retrieval status. No paid API keys, no synthetic holdings.
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import re
import urllib.error
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SOURCE = ROOT / 'config/kbty_sec_registry.json'
OUTPUT = ROOT / 'data/kbty_sec.json'
SEC_SUBMISSIONS = 'https://data.sec.gov/submissions/CIK0000919160.json'
SEC_FULLTEXT = 'https://efts.sec.gov/LATEST/search-index'
SEC_ARCHIVE = 'https://www.sec.gov/Archives/edgar/data/919160'
SERIES = 'S000109351'
CIK = '0000919160'
MAX_HEADER_CHECKS = 10
INTERESTING_FORMS = frozenset({
    '485APOS', '485BPOS', '485BXT', '497', '497K',
    '8-A12B', '8-A12B/A', 'EFFECT', 'N-PORT', 'NPORT-P',
    'N-CSR', 'N-CEN', '24F-2NT', 'CERT'
})
ACCESSION_RE = re.compile(r'^\d{10}-\d{2}-\d{6}$')
FILENAME_RE = re.compile(r'^[A-Za-z0-9._-]{1,200}$')
SERIES_RE = re.compile(r'<SERIES-ID>\s*S000109351(?:\b|<)', re.I)

FORM_CONTEXT = {
    'CERT': ('NYSE Arca 상장·등록 승인 확인서',
             '거래소가 KBTY 지분의 상장·등록 승인을 SEC에 확인한 문서입니다. 실제 첫 거래 체결, AUM 또는 APR 편입을 증명하지 않습니다.'),
    '485APOS': ('등록신고서 개정 제출',
                 'KBTY 시리즈의 등록신고 개정서가 제출됐습니다. 구체적인 변경사항과 효력 여부는 SEC 원문 확인이 필요합니다.'),
    '485BPOS': ('투자설명서 등 등록문서 개정',
                 'KBTY 관련 등록문서 변경신고가 제출됐습니다. 보수·구성종목·전략 변경 여부는 원문을 검토해야 합니다.'),
    '485BXT': ('등록신고 효력 발생일 관련 서류',
                 'KBTY 관련 등록신고 효력일 조정 서류가 제출됐습니다. 효력일 변경만으로 상장·거래 개시를 확인할 수 없습니다.'),
    '497': ('투자설명서·최종자료 제출',
             'KBTY 관련 최종 공모자료 제출을 감지했습니다. 자료의 세부 내용과 실제 거래 여부는 원문·운용사 공시로 재확인해야 합니다.'),
    '497K': ('요약 투자설명서 제출',
              'KBTY 관련 요약 투자설명서 제출을 감지했습니다. 핵심 조건 변경 여부는 해당 원문을 확인해야 합니다.'),
    '8-A12B': ('거래소 등록 관련 신고',
                'KBTY 관련 거래소 증권 등록신고를 감지했습니다. 이는 첫 거래일 확정이나 실제 거래량 발생과 다릅니다.'),
    'EFFECT': ('등록신고 효력 발생 통지',
               'KBTY 관련 효력 발생 통지를 감지했습니다. ETF 실제 거래 개시는 별도로 확인해야 합니다.'),
    'NPORT-P': ('보유자산 정기 보고',
                 'KBTY의 정기 포트폴리오 보고 제출을 감지했습니다. 에이피알 보유비중·주식 수는 정식 운용사 구성종목 파일과 교차 검증해야 합니다.'),
    'N-CSR': ('주주보고서 제출',
               'KBTY 관련 주주보고서 제출을 감지했습니다. 실제 자산·보유종목·재무내용은 원문 검토가 필요합니다.'),
}
DEFAULT_CONTEXT = ('SEC 정기 공시 제출',
                   'KBTY 시리즈의 SEC 제출 문서를 확인했습니다. 개별 데이터와 투자 영향은 원문 검토가 필요합니다.')


def read_json(path, default):
    try:
        return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return default


def write_json(path, value):
    target = Path(path)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(value, ensure_ascii=False, indent=2) + '\n',
                      encoding='utf-8')


def sec_fetch(url: str) -> bytes:
    # SEC fair-access: identifiable user agent, no impersonation or credentials.
    # An operator can set SEC_USER_AGENT to its own descriptive contact identity.
    agent = os.environ.get('SEC_USER_AGENT') or (
        'APR-SIGNAL free public research '
        '(contact: https://github.com/sungwookmay-stack/apr-signal/issues)')
    req = urllib.request.Request(url, headers={
        'User-Agent': agent, 'Accept': 'application/json,text/html,*/*',
        'Accept-Encoding': 'identity'})
    with urllib.request.urlopen(req, timeout=14) as response:
        return response.read(1_500_000)


def failure_detail(exc, endpoint):
    """Safe operational diagnostics, never URLs, response bodies or credentials."""
    status = getattr(exc, 'code', None)
    reason = ('접근 거절 · 우회하지 않고 기존 확인자료 유지' if status == 403 else
              '호출 제한 · 다음 예약 조회까지 대기' if status == 429 else
              '원천 조회 실패 · 기존 확인자료 유지')
    return {'endpoint': endpoint, 'error_type': type(exc).__name__,
            'http_status': status if isinstance(status, int) else None,
            'note': reason}


def candidate_filings(payload, min_date='2026-07-01'):
    """Inspect trust-wide submission arrays, never identify KBTY at this stage."""
    if not isinstance(payload, dict):
        raise ValueError('SEC submissions JSON structure unavailable')
    cik = str(payload.get('cik', '')).zfill(10)
    if cik != CIK:
        raise ValueError('SEC CIK does not match Guinness Atkinson Funds')
    recent = (payload.get('filings') or {}).get('recent') or {}
    keys = ('accessionNumber', 'filingDate', 'form', 'primaryDocument')
    if not all(isinstance(recent.get(k), list) for k in keys):
        raise ValueError('SEC recent filings arrays are incomplete')
    rows = []
    n = min(len(recent[k]) for k in keys)
    for i in range(n):
        accession = str(recent['accessionNumber'][i])
        date = str(recent['filingDate'][i])
        form = str(recent['form'][i]).upper()
        filename = str(recent['primaryDocument'][i])
        if (not ACCESSION_RE.fullmatch(accession) or
            not re.fullmatch(r'20\d\d-\d\d-\d\d', date) or
            date < min_date or form not in INTERESTING_FORMS or
            not FILENAME_RE.fullmatch(filename)):
            continue
        rows.append({'accession': accession, 'filed_date': date,
                     'form': form, 'filename': filename})
    return sorted(rows, key=lambda x: (x['filed_date'], x['accession']),
                  reverse=True)


def fulltext_url(on_date):
    """SEC's free EDGAR full-text search, filtered to the correct trust CIK."""
    params = urllib.parse.urlencode({
        'q': '"Guinness Atkinson K-Beauty ETF"',
        'ciks': CIK,
        'dateRange': 'custom',
        'startdt': '2026-10-01',
        'enddt': on_date.strftime('%Y-%m-%d')
    })
    return SEC_FULLTEXT + '?' + params


def fulltext_candidates(payload, min_date='2026-10-01'):
    """SEC EFTS hits can be exhibits or unrelated funds: CIK filter is REQUIRED.

    Returned entries are only *candidates*. Caller must fetch exact filing
    index headers and check KBTY's series ID before publishing a new filing.
    """
    hits = (payload.get('hits') or {}).get('hits') if isinstance(payload, dict) else None
    if not isinstance(hits, list):
        raise ValueError('SEC full-text response not recognized')
    result = {}
    for hit in hits[:100]:
        if not isinstance(hit, dict):
            continue
        source = hit.get('_source') or {}
        if not isinstance(source, dict):
            continue
        ciks = source.get('ciks') or []
        if not isinstance(ciks, list):
            ciks = [ciks]
        if CIK not in {str(v).zfill(10) for v in ciks}:
            continue
        ident = str(hit.get('_id') or '')
        accession, sep, file = ident.partition(':')
        if not sep or not ACCESSION_RE.fullmatch(accession):
            continue
        date = str(source.get('file_date') or '')
        form = str(source.get('form') or '').upper()
        if not re.fullmatch(r'20\d\d-\d\d-\d\d', date):
            continue
        if date < min_date or form not in INTERESTING_FORMS:
            continue
        # The search hit may be an exhibit; link new records to the SEC
        # filing index, not to an unrelated attachment.
        result[accession] = {
            'accession': accession, 'filed_date': date, 'form': form,
            'filename': accession + '-index.htm'
        }
    return sorted(result.values(), key=lambda x:(x['filed_date'],x['accession']),
                  reverse=True)


def filing_link(accession, filename):
    if not ACCESSION_RE.fullmatch(accession) or not FILENAME_RE.fullmatch(filename):
        raise ValueError('Unsafe SEC filing path')
    return SEC_ARCHIVE + '/' + accession.replace('-', '') + '/' + filename


def has_target_series(header_content):
    text = (header_content.decode('utf-8', errors='replace')
            if isinstance(header_content, bytes) else str(header_content))
    return bool(SERIES_RE.search(text))


def certificate_identity(header, item, transport):
    """CERT may lack SERIES-ID. Verify exact fund name in the official PDF.

    Never accept CIK, filename, or search snippets alone as fund identity.
    """
    from html import unescape
    import io
    from pypdf import PdfReader
    text = unescape(header.decode('utf-8', errors='replace'))
    if not re.search(r'<CIK>\s*0000919160\b', text, re.I):
        return False
    filename = item['filename']
    if not filename.lower().endswith('.pdf'):
        match = re.search(r'<FILENAME>\s*([A-Za-z0-9._-]+\.pdf)\b', text, re.I)
        if not match:
            return False
        filename = match.group(1)
    payload = transport(filing_link(item['accession'], filename))
    try:
        document = PdfReader(io.BytesIO(payload))
        content = ' '.join((page.extract_text() or '') for page in document.pages[:10])
    except Exception as exc:
        raise ValueError('CertificatePDFUnreadable') from None
    content = re.sub(r'\s+', ' ', content)
    return bool(re.search(r'Guinness Atkinson K[-–]Beauty ETF\b', content, re.I)
                and re.search(r'NYSE Arca', content, re.I)
                and re.search(r'certifies its approval for listing and registration', content, re.I))


def make_detected_record(item):
    title, note = FORM_CONTEXT.get(item['form'], DEFAULT_CONTEXT)
    return {
        'accession': item['accession'],
        'filed_date': item['filed_date'],
        'form': item['form'],
        'title_ko': title,
        'summary_ko': note,
        'change_ko': '자동 검출·시리즈 확인 완료. 공시 본문의 세부 변경내용은 아직 검토하지 않았습니다.',
        'stage': '신규 SEC 제출',
        'source_url': filing_link(item['accession'], item['filename']),
        'review_level': 'KBTY 시리즈 확인 · 서식 기반 설명'
    }


def assemble_base(registry, previous=None, checked_at=None):
    previous = previous if isinstance(previous, dict) else {}
    items = {x['accession']: dict(x) for x in registry.get('filings', [])
             if ACCESSION_RE.fullmatch(str(x.get('accession', '')))}
    for old in previous.get('filings', []):
        if not isinstance(old, dict):
            continue
        accession = old.get('accession', '')
        # Keep a previously series-confirmed item, but curated registry takes
        # priority over generic automatically assigned notes.
        if (ACCESSION_RE.fullmatch(str(accession)) and
            old.get('review_level') in ('KBTY 시리즈 확인 · 서식 기반 설명', 'CERT 원문 펀드명·거래소 확인') and
            accession not in items and
            str(old.get('source_url', '')).startswith(SEC_ARCHIVE)):
            items[accession] = old
    filings = sorted(items.values(),
                     key=lambda x: (x['filed_date'], x['accession']),
                     reverse=True)
    return {
        'fund': registry.get('fund'),
        'ticker': 'KBTY',
        'registrant_cik': CIK,
        'series_id': SERIES,
        'reviewed_date': registry.get('reviewed_date'),
        'sec_filer_page': registry.get('sec_filer_page'),
        'official_fund_page': registry.get('official_fund_page'),
        'checked_at_utc': checked_at,
        'last_successful_check_utc': previous.get('last_successful_check_utc'),
        'latest_verified_filing_date': filings[0]['filed_date'] if filings else None,
        'sec_monitor_status': '공식 SEC 제출목록 조회 전 · 기존 공시 검토자료 표시',
        'sec_monitor_error': None,
        'scan_count': 0,
        'new_detected': 0,
        'briefing': registry.get('briefing', []),
        'watchlist': registry.get('watchlist', []),
        'filings': filings,
        'data_scope': 'SEC 공시 검증 여부와 운용사 실제 상장·AUM·APR 편입은 별도',
        'summary_basis': '검토자료는 SEC 본문 기반. 자동 추가는 KBTY 시리즈 또는 CERT 원문 펀드명·거래소 확인 기반.'
    }


def refresh(transport=None, output=OUTPUT, registry_file=SOURCE, now=None):
    """Verify recent EDGAR filings, persist Korean digest without paywall."""
    transport = transport or sec_fetch
    now = now or dt.datetime.now(dt.timezone.utc)
    registry = read_json(registry_file, {})
    if registry.get('series_id') != SERIES or registry.get('cik') != CIK:
        raise ValueError('KBTY registry identity mismatch')
    previous = read_json(output, {})
    report = assemble_base(registry, previous,
                           now.astimezone(dt.timezone.utc).isoformat(timespec='seconds'))
    report['retrieval_diagnostics'] = []
    report['pending_review'] = []
    seen = {x['accession'] for x in report['filings']}
    try:
        source_name = 'SEC submissions'
        try:
            raw = transport(SEC_SUBMISSIONS)
            listings = candidate_filings(json.loads(raw.decode('utf-8')))
        except (OSError, ValueError, KeyError, TimeoutError,
                urllib.error.URLError) as initial_error:
            report['retrieval_diagnostics'].append(failure_detail(initial_error, source_name))
            # The SEC data host may block some cloud IP ranges. Try its
            # separate official full-text index before reporting failure.
            source_name = 'SEC full-text'
            raw = transport(fulltext_url(now.date()))
            listings = fulltext_candidates(json.loads(raw.decode('utf-8')))
        checked = 0
        header_errors = 0
        newest_known = report['latest_verified_filing_date'] or '2026-07-01'
        possible = [x for x in listings if
                    x['accession'] not in seen and x['filed_date'] >= newest_known]
        for item in possible[:MAX_HEADER_CHECKS]:
            checked += 1
            header = filing_link(item['accession'],
                                 item['accession'] + '-index-headers.html')
            try:
                body = transport(header)
                certificate = item['form'] == 'CERT'
                verified = certificate_identity(body, item, transport) if certificate else has_target_series(body)
                if not verified:
                    if certificate:
                        report['pending_review'].append({'accession': item['accession'], 'form': 'CERT', 'filed_date': item['filed_date'], 'reason': 'CERT 원문 펀드 식별 미확인'})
                    continue
                record = make_detected_record(item)
                if certificate:
                    record['review_level'] = 'CERT 원문 펀드명·거래소 확인'
                    record['change_ko'] = '공식 PDF의 펀드명·거래소 상장등록 승인 문구 확인. 실제 거래 개시·보유자산은 별도입니다.'
                report['filings'].append(record)
                seen.add(item['accession'])
            except (OSError, ValueError, ImportError, TimeoutError, urllib.error.URLError) as header_error:
                report['retrieval_diagnostics'].append(failure_detail(header_error, 'SEC filing header'))
                # Fail closed: a header fetch failure is not a KBTY filing.
                header_errors += 1
                continue
        report['filings'].sort(key=lambda x: (x['filed_date'], x['accession']),
                               reverse=True)
        report['latest_verified_filing_date'] = (
            report['filings'][0]['filed_date'] if report['filings'] else None)
        report['new_detected'] = len(seen) - len(set(
            x['accession'] for x in assemble_base(registry, previous)['filings']))
        report['scan_count'] = checked
        if report['pending_review']:
            report['sec_monitor_status'] = source_name + ' 조회 완료 · CERT 원문 식별 검토 대기 (최신 확인 미완료)'
            report['sec_monitor_error'] = 'CertificateIdentityUnverified'
        elif checked and header_errors:
            report['sec_monitor_status'] = (
                source_name + ' 검색 완료 · 개별 공시 확인 일부 실패; '
                '신규공시 최신 여부는 미확정'
            )
            report['sec_monitor_error'] = 'SECHeaderUnavailable'
        elif len(possible) > MAX_HEADER_CHECKS:
            report['sec_monitor_status'] = (
                source_name + ' 일부 공시 확인 · 검증 범위 제한'
            )
        else:
            report['sec_monitor_status'] = (
                source_name + ' 대상 서식 조회 완료 · KBTY 식별 확인 공시만 표시'
            )
            report['last_successful_check_utc'] = report['checked_at_utc']
    except (OSError, ValueError, KeyError, TimeoutError, urllib.error.URLError) as exc:
        report['sec_monitor_status'] = (
            'SEC 자동 접근 실패 · 기존 확인 공시 유지 (최신 여부 미확인)')
        report['sec_monitor_error'] = type(exc).__name__
        report['retrieval_diagnostics'].append(failure_detail(exc, source_name))
    write_json(output, report)
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--refresh', action='store_true',
                        help='Check current free SEC submissions and KBTY filing headers')
    args = parser.parse_args()
    if args.refresh:
        result = refresh()
    else:
        registry = read_json(SOURCE, {})
        result = assemble_base(registry, read_json(OUTPUT, {}))
        write_json(OUTPUT, result)
    print(json.dumps({
        'status': result['sec_monitor_status'],
        'latest_verified': result['latest_verified_filing_date'],
        'filings': len(result['filings']),
        'new_series_verified': result['new_detected'],
        'sec_checked_at_utc': result['checked_at_utc'],
        'error_type': result['sec_monitor_error']
    }, ensure_ascii=False))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
