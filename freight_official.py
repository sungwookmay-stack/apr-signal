#!/usr/bin/env python3
"""Read monthly Customs sea export transportation-cost release, free/no key.

This is customs-reported average cost PER 2 TEU (40ft), including surcharges;
it is NOT a spot-freight index or APR's actual billed freight rate.

Discovery is best-effort.  No unpublished month/number is synthesized.
"""
from __future__ import annotations
import datetime as dt
import html
from html.parser import HTMLParser
import re
from urllib import parse

BASE = 'https://www.customs.go.kr'
LIST_URL = BASE + '/kcs/na/ntt/selectNttList.do?bbsId=1362&mi=2891'
KNOWN_RELEASES = {
    '2026-09': BASE+'/kcs/na/ntt/selectNttInfo.do?bbsId=1362&mi=2891&nttSn=10179764&nttSnUrl=85ecfa8eed3f4098ece86ef6db0520a7',
}

def strip_markup(body):
    text = html.unescape(re.sub(r'(?is)<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>', ' ', body))
    text = re.sub(r'(?s)<[^>]*>', ' ', text).replace('\xa0', ' ')
    return re.sub(r'\s+', ' ', text)


def parse_release(text, url):
    """Accept only explicit Customs 'sea EXPORT' rows for one dated month."""
    content = strip_markup(text)
    date = re.search(r'(20\d{2})\s*년\s*(0?[1-9]|1[0-2])\s*월\s*수출입\s*운송비용\s*현황', content)
    if not date:
        return None
    year, month = int(date.group(1)), int(date.group(2))
    if not (year == 2026 and 5 <= month <= 12):
        return None
    start = re.search(r'(?:□\s*)?[〔［\[]\s*해상\s*수출\s*[〕］\]]', content)
    if not start:
        return None
    tail = content[start.end():]
    stop = re.search(r'(?:□\s*)?[〔［\[]\s*해상\s*수입\s*[〕］\]]', tail)
    if stop:
        tail = tail[:stop.start()]
    # Values also appear in explanatory comparisons; only the first table
    # section is considered to avoid confusing last month's comparison values.
    m = re.search(r'<\s*해상\s*수출\s*운송비용\s*현황\s*>', tail)
    if m:
        tail = tail[:m.start()]
    result = {}
    labels = {'us_west': r'미국\s*서부', 'us_east': r'미국\s*동부',
              'eu': r'유럽\s*연합'}
    for key, name in labels.items():
        match = re.search(name+r'\s*[\|:]?\s*(\d[\d,]*)\s*천\s*원', tail)
        if not match:
            return None
        value = int(match.group(1).replace(',', ''))
        if not 300 < value < 30000:
            return None
        result[key] = value
    result['month'] = f'{year:04d}-{month:02d}'
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
        self.anchor = {'href': a.get('href') or '', 'onclick': a.get('onclick') or '',
                       'text': []}

    def handle_data(self, data):
        if self.anchor is not None:
            self.anchor['text'].append(data)

    def handle_endtag(self, tag):
        if tag.lower() != 'a' or self.anchor is None:
            return
        a = self.anchor
        self.anchor = None
        title = ' '.join(a['text'])
        m = re.search(r'(20\d{2})\s*년\s*(\d{1,2})\s*월\s*수출입\s*운송비용\s*현황', title)
        if not m:
            return
        month = f'{int(m.group(1)):04d}-{int(m.group(2)):02d}'
        link = html.unescape(a['href'])
        if not (link.startswith('/') or link.startswith(BASE)):
            link = ''
        if 'selectNttInfo.do' not in link or 'nttSn=' not in link:
            match = re.search(r'(?:nttSn=|["\'])\s*(\d{7,12})(?:\b|["\'])',
                              a['href']+' '+a['onclick'])
            if not match:
                return
            link = f'{BASE}/kcs/na/ntt/selectNttInfo.do?bbsId=1362&mi=2891&nttSn={match.group(1)}'
        elif link.startswith('/'):
            link = parse.urljoin(BASE, link)
        if parse.urlparse(link).hostname not in ('customs.go.kr', 'www.customs.go.kr'):
            return
        self.links.append((month, link))


def collect_release_links(html_body):
    parser = ReleaseLinkParser()
    parser.feed(html_body)
    return parser.links


def fetch_latest(get_bytes, today=None, pages=4):
    """Return (row, official_link), or raise if no reliable official release.

    The caller supplies a standard-library fetch function.  Tests inject
    fixtures; no third-party packages or paid APIs are needed.
    """
    today = today or dt.date.today()
    candidates = dict(KNOWN_RELEASES)
    index_errors = []
    for page in range(1, pages+1):
        url = LIST_URL + '&pageIndex=' + str(page)
        try:
            doc = get_bytes(url, timeout=9).decode('utf-8', errors='replace')
            for month, link in collect_release_links(doc):
                candidates[month] = link
        except Exception as exc:
            index_errors.append(type(exc).__name__)
            if page >= 2:
                break
    for month in sorted(candidates, reverse=True):
        if month > today.strftime('%Y-%m') or month < '2026-05':
            continue
        url = candidates[month]
        try:
            doc = get_bytes(url, timeout=12).decode('utf-8', errors='replace')
            row = parse_release(doc, url)
            if row and row['month'] == month:
                return row, url
        except Exception as exc:
            index_errors.append(type(exc).__name__)
    raise ValueError('관세청 공식 해상수출 운송비용 표 미확인' +
                     (' (접속 오류: '+','.join(index_errors[:3])+')' if index_errors else ''))
