"""Conservative parsing of the issuer's public KBTY page.

A future launch date, index composition and Top 10 are not a live portfolio.
Never infer a reporting date from the fetch time or infer zero from missing data.
"""
import datetime as dt
from html import unescape
import re


def parse_official(document):
    text = re.sub(r'\s+', ' ', re.sub(r'<[^>]+>', ' ', unescape(document)))
    out = {'launch_expected': None, 'launch_expected_date': None,
           'official_data_state': 'not_published', 'official_metrics': {}}
    match = re.search(r'expected to begin trading(?: on NYSE Arca on)?\s+(\w+ \d{1,2}, \d{4})', text, re.I)
    if match:
        try:
            day = dt.datetime.strptime(match.group(1), '%B %d, %Y').date().isoformat()
            out.update(launch_expected=day+' (공식 예정일, 실제 거래 개시 확인 아님)',
                       launch_expected_date=day, status=day+' 거래 개시 예정 (공식 사이트)')
        except ValueError:
            pass
    elif 'expected to begin trading in the second week of November' in text:
        out.update(status='11월 둘째 주 상장 예정 문구 확인 (공식 사이트)',
                   launch_expected='11월 둘째 주 (현재 공식 페이지 문구, 변경 가능)')
    elif 'Launching November 2026' in text or 'Coming soon' in text:
        out['status']='출시 준비 중 (공식 사이트)'
    out['holdings_publication_state'] = ('not_published' if 'Holdings will appear here' in text else 'unverified')
    facts = re.search(r'Fund facts(.{0,3500}?)Performance', text, re.I)
    if not facts:
        out['official_data_state']='unrecognized_page'
        return out
    # Only labelled facts, never NAV definition, management fees, or marketing numbers.
    for key, label in [('nav_usd',r'NAV'), ('aum_usd',r'(?:Net assets|Total net assets)'),
                       ('closing_market_price_usd',r'Closing market price')]:
        m = re.search(r'\b'+label+r'\s*[:]?\s*\$\s*([\d,]+(?:\.\d+)?)\s*([MB])?\b', facts.group(1), re.I)
        if m:
            val=float(m.group(1).replace(',','')) * {'M':1e6,'B':1e9}.get((m.group(2) or '').upper(),1)
            if val>0:
                out['official_metrics'][key]={'value':val,'as_of':None,'date_state':'not_published'}
    if out['official_metrics']:
        out['official_data_state']='values_without_verified_as_of'
    return out
