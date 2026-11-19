"""Conservative parsing of the issuer's public KBTY page.

A future launch date, index composition and Top 10 are not a live portfolio.
Never infer a reporting date from the fetch time or infer zero from missing data.
"""
import datetime as dt
from html import unescape
import re


def us_date(raw):
    try:return dt.datetime.strptime(raw, '%m/%d/%Y').date().isoformat()
    except (TypeError,ValueError):return None


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
    if re.search(r'KBTY is now trading on NYSE Arca', text, re.I):
        out.update(status='NYSE Arca 거래 중 (운용사 공식 확인)', trading_confirmed=True)
        inception=re.search(r'ETF inception\s+(\d{1,2}/\d{1,2}/\d{4})',text,re.I)
        if inception:out['inception_date']=us_date(inception.group(1))
    latest=re.search(r'KBTY Top 10 Holdings\s+as of\s+(\d{1,2}/\d{1,2}/\d{4})(.*?)(?:KBTY Top 10 Holdings|$)',text,re.I)
    if latest:
        day=us_date(latest.group(1))
        # The issuer provides ticker, instrument type, USD price, shares and USD value.
        row=re.search(r'([\d.]+)%\s+A?278470\s+APR CORP(?:/KOREA)?\s+COMMON STOCK\s+[\d,.]+\s+([\d,]+)\s+([\d,.]+)\s+[A-Z0-9]{9}\b',latest.group(2),re.I)
        if day and row and 0<=float(row.group(1))<=100:
            out.update(holdings_publication_state='published',issuer_apr={
                'ticker':'A278470','name':'APR CORP/KOREA','weight_pct':float(row.group(1)),
                'shares':int(row.group(2).replace(',','')),'market_value_usd':float(row.group(3).replace(',','')),'as_of':day})
    facts = re.search(r'Fund facts(.{0,3500}?)Performance', text, re.I)
    if not facts:
        out['official_data_state']='unrecognized_page'
        return out
    # Only labelled facts, never NAV definition, management fees, or marketing numbers.
    for key, label in [('nav_usd',r'NAV'), ('aum_usd',r'(?:Net assets|Total net assets)'),
                       ('closing_market_price_usd',r'Closing market price')]:
        m = re.search(r'\b'+label+r'\s*(?:\((\d{1,2}/\d{1,2}/\d{4})\))?\s*[:]?\s*\$\s*([\d,]+(?:\.\d+)?)\s*([MB])?\b', facts.group(1), re.I)
        if m:
            val=float(m.group(2).replace(',','')) * {'M':1e6,'B':1e9}.get((m.group(3) or '').upper(),1)
            day=us_date(m.group(1))
            if val>0:
                out['official_metrics'][key]={'value':val,'as_of':day,'date_state':'issuer_published' if day else 'not_published'}
    if out['official_metrics']:
        out['official_data_state']='dated_issuer_data' if any(r.get('as_of') for r in out['official_metrics'].values()) else 'values_without_verified_as_of'
    return out
