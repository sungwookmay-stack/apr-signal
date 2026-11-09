#!/usr/bin/env python3
"""Read official Korea Customs monthly sea-export transport-cost bulletins.

Amounts are KRW thousands per 2 TEU, INCLUDING shipping surcharges/fees.
They are NOT spot freight quotations or APR's actual contractual prices.
Only dated monthly Customs releases are used; unavailable routes stay missing.
"""
from __future__ import annotations

import datetime as dt
import html
from html.parser import HTMLParser
import re
from urllib import parse

BASE = 'https://www.customs.go.kr'
LIST_URL = BASE + '/kcs/na/ntt/selectNttList.do?bbsId=1362&mi=2891'
MIN_MONTH = '2025-06'
ROUTES = {
    'us_west': r'미국\s*서부',
    'us_east': r'미국\s*동부',
    'eu': r'유럽\s*연합',
    'middle_east': r'중동',
    'china': r'중국',
    'japan': r'일본',
    'vietnam': r'베트남',
}
# Verified links to official monthly bulletins. These also permit historical
# backfill if the Customs list no longer includes older releases.
# Never invent IDs or fill monthly observations with interpolated estimates.
_IDS = {
    '2025-06': '10145684',
    '2025-07': '10149246',
    '2025-09': '10152047',
    '2025-10': '10152649',
    '2025-11': '10153245',
    '2025-12': '10153744',
    '2026-01': '10155384',
    '2026-03': '10161406',
    '2026-04': '10164145',
    '2026-05': '10166825',
    '2026-06': '10170124',
    '2026-07': '10173585',
    '2026-08': '10176744',
    '2026-09': '10179764',
}
KNOWN_RELEASES = {
    month: BASE+'/kcs/na/ntt/selectNttInfo.do?bbsId=1362&mi=2891&nttSn='+num
    for month, num in _IDS.items()
}
# Customs requires nttSnUrl in its accessible canonical article links.
# A bare nttSn URL may return an empty/not-found article on the live host.
_VERIFIED_HASHES = {
    '2025-06': '017b2422f80aa4f518d64af965679ac9',
    '2025-07': '3f4ee0a9eb59169b4cf34f0e5e68c56d',
    '2025-09': '4e3e05639139a1a8f7d29e6b2211a61c',
    '2025-10': 'd302ddd61498f56147b3cc2e63c53c40',
    '2025-11': 'fd29d22ac4a7eeb6c7828cc2a9ef1c76',
    '2025-12': 'a00de2f6c5858bad1f61c904e6c985c0',
    '2026-01': '32dbf92626ff0503f22d8eabdb86f919',
    '2026-03': 'a9b44ec42b1e74b12d0e7e51e15fd3e7',
    '2026-04': 'a339ef9693d02f8149fabbcaadc1ecbe',
    '2026-05': '7165f29308d85363e87120ca30b47f4c',
    '2026-06': 'dc430818d80eca09eafad1c3858cb47e',
    '2026-07': '623b71ead9d2c77d728a59d8fee6b3ed',
    '2026-08': '3d882ad4c9ae38a38038fe09e94c70bf',
    '2026-09': '85ecfa8eed3f4098ece86ef6db0520a7',
}
for _month, _token in _VERIFIED_HASHES.items():
    KNOWN_RELEASES[_month] += '&nttSnUrl=' + _token


def strip_markup(body):
    text = html.unescape(re.sub(
        r'(?is)<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>',
        ' ', body))
    text = re.sub(r'(?s)<[^>]*>', ' ', text).replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', text)


def parse_release(text, url):
    """Read only the FIRST sea-export table, never sea imports or air imports.

    Older (2025) bulletins do not have a Middle East route. Optional missing
    routes are omitted instead of being interpreted as zero.
    """
    content = strip_markup(text)
    date = re.search(
        r'(20\d{2})\s*년\s*(0?[1-9]|1[0-2])\s*월\s*수출입\s*운송비용\s*현황',
        content)
    if not date:
        return None
    month = f'{int(date.group(1)):04d}-{int(date.group(2)):02d}'
    if month < MIN_MONTH:
        return None
    start = re.search(r'(?:□\s*)?[〔［\[]\s*해상\s*수출\s*[〕］\]]', content)
    if not start:
        return None
    tail = content[start.end():]
    stop = re.search(r'(?:□\s*)?[〔［\[]\s*해상\s*수입\s*[〕］\]]', tail)
    if stop:
        tail = tail[:stop.start()]
    # Do not let explanatory comparisons below the export table turn into
    # false route values if a required table cell goes missing.
    end = re.search(r'<\s*해상\s*수출\s*운송비용\s*현황\s*>', tail)
    if not end:
        end = re.search(r'[＜<]\s*해상\s*수출\s*운송비용\s*현황\s*[＞>]', tail)
    if end:
        tail = tail[:end.start()]
    result = {}
    for key, label in ROUTES.items():
        match = re.search(
            label+r'\s*[\|:]?\s*(\d[\d,]*)\s*천\s*원', tail)
        if not match:
            if key in ('us_west', 'us_east', 'eu'):
                return None
            continue
        value = int(match.group(1).replace(',', ''))
        if not 300 < value < 30000:
            if key in ('us_west', 'us_east', 'eu'):
                return None
            continue
        result[key] = value
    result['month'] = month
    return result


class ReleaseLinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.anchor = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != 'a':
            return
        a = dict(attrs)
        self.anchor = {'href': a.get('href') or '',
                       'onclick': a.get('onclick') or '', 'text': []}

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor['text'].append(data)

    def handle_endtag(self, tag):
        if tag.lower() != 'a' or self.anchor is None:
            return
        a = self.anchor
        self.anchor = None
        title = ' '.join(a['text'])
        m = re.search(
            r'(20\d{2})\s*년\s*(\d{1,2})\s*월\s*수출입\s*운송비용\s*현황',
            title)
        if not m:
            return
        month = f'{int(m.group(1)):04d}-{int(m.group(2)):02d}'
        link = html.unescape(a['href'])
        if not (link.startswith('/') or link.startswith(BASE)):
            link = ''
        if 'selectNttInfo.do' not in link or 'nttSn=' not in link:
            match = re.search(
                r'(?:nttSn=|["\'])\s*(\d{7,12})(?:\b|["\'])',
                a['href']+' '+a['onclick'])
            if not match:
                return
            link = (BASE+'/kcs/na/ntt/selectNttInfo.do?'
                    'bbsId=1362&mi=2891&nttSn='+match.group(1))
        elif link.startswith('/'):
            link = parse.urljoin(BASE, link)
        if parse.urlparse(link).hostname not in (
                'customs.go.kr', 'www.customs.go.kr'):
            return
        self.links.append((month, link))


def collect_release_links(html_body):
    parser = ReleaseLinkParser()
    parser.feed(html_body)
    return parser.links


def discover_releases(get_bytes, pages=4):
    candidates = dict(KNOWN_RELEASES)
    errors = []
    for page in range(1, pages+1):
        url = LIST_URL + '&pageIndex=' + str(page)
        try:
            doc = get_bytes(url, timeout=9).decode('utf-8', errors='replace')
            for month, link in collect_release_links(doc):
                if month not in candidates or 'nttSnUrl=' in link:
                    candidates[month] = link
        except Exception as exc:
            errors.append(type(exc).__name__)
            if page >= 2:
                break
    return candidates, errors


def fetch_latest(get_bytes, today=None, pages=4):
    """Return (verified row, official URL), or raise on inaccessible releases."""
    today = today or dt.date.today()
    candidates, errors = discover_releases(get_bytes, pages)
    for month in sorted(candidates, reverse=True):
        if month > today.strftime('%Y-%m') or month < MIN_MONTH:
            continue
        url = candidates[month]
        try:
            doc = get_bytes(url, timeout=12).decode('utf-8', errors='replace')
            row = parse_release(doc, url)
            if row and row['month'] == month:
                return row, url
        except Exception as exc:
            errors.append(type(exc).__name__)
    raise ValueError('관세청 공식 해상수출 운송비용 표 미확인' +
                     (' (접속 오류: '+','.join(errors[:3])+')'
                      if errors else ''))


def fetch_history(get_bytes, previous=(), today=None, pages=0,
                  max_fetch=24):
    """Backfill/reverify historical observations once, without fabricated data.

    Existing rows with official per-month source_url are not fetched again.
    Unverified legacy three-route rows are replaced only if the actual dated
    official release is parsed successfully. Returns (new rows, failures).
    """
    today = today or dt.date.today()
    candidates, errors = discover_releases(get_bytes, pages)
    previous_by_month = {r['month']: r for r in previous if r.get('month')}
    updates = []
    attempted = 0
    for month in sorted(candidates, reverse=True):
        if month < MIN_MONTH or month > today.strftime('%Y-%m'):
            continue
        existing = previous_by_month.get(month) or {}
        if existing.get('source_url') and all(
                existing.get(key) is not None for key in
                ('us_west', 'us_east', 'eu')):
            continue
        if attempted >= max_fetch:
            break
        attempted += 1
        url = candidates[month]
        try:
            doc = get_bytes(url, timeout=12).decode('utf-8', errors='replace')
            row = parse_release(doc, url)
            if not row or row['month'] != month:
                errors.append(month+': 표 정합성 검증 실패')
                continue
            row['source_url'] = url
            updates.append(row)
        except Exception as exc:
            errors.append(month+': '+type(exc).__name__)
    return updates, errors
