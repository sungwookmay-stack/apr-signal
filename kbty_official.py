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


HOLDINGS_HEADER = re.compile(r'KBTY\s+(?:Top\s+10\s+)?Holdings\s+as\s+of\s+(\d{1,2}/\d{1,2}/\d{4})', re.I)
APR_ROW = re.compile(
    r'(?<![\d.])(\d+(?:\.\d+)?)\s*%\s+A?278470\s+APR CORP(?:/KOREA)?\s+'
    r'COMMON STOCK\s+\$?([\d,.]+)\s+([\d,]+)\s+\$?([\d,.]+)\s+Y0R9CJ118\b', re.I)


def apr_holdings_rows(text):
    """Return issuer-dated APR shares held; never infer zero for a missing row."""
    dates = list(HOLDINGS_HEADER.finditer(text))
    results, conflicts = {}, set()
    for i, heading in enumerate(dates):
        end = dates[i+1].start() if i+1 < len(dates) else len(text)
        day = us_date(heading.group(1))
        if day is None:
            continue
        segment = text[heading.end():end]
        for found in APR_ROW.finditer(segment):
            weight, price, count, value = [x.replace(',','') for x in found.groups()]
            try:
                weight, price, count, value = float(weight), float(price), int(count), float(value)
            except ValueError:
                continue
            # Prices are shown to cents, and value may use extra precision.
            if not 0 <= weight <= 100 or not 0 < count <= 1e12 or not 0 < price <= 1e6:
                continue
            if value <= 0 or abs(price*count-value) > .006*count+.02:
                continue
            row = {'ticker':'A278470', 'name':'APR CORP/KOREA','weight_pct':weight,
                   'shares':count,'market_value_usd':value,'as_of':day}
            if day in results and row != results[day]:
                conflicts.add(day)
            results[day] = row
    return [results[d] for d in sorted(results.keys()-conflicts)]


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
    observations = apr_holdings_rows(text)
    if observations:
        out.update(holdings_publication_state='published',
                   issuer_apr=observations[-1],
                   issuer_apr_history=observations)
    # The navigation repeats these headings before the actual fund facts.
    # A repeated start heading ends a block rather than swallowing the next one.
    blocks = re.findall(r'\bFund facts\b(.{0,3500}?)(?=\b(?:Performance|Fund facts)\b)', text, re.I)
    if not blocks:
        out['official_data_state']='unrecognized_page'
        return out
    # Only labelled facts, never NAV definition, management fees, or marketing numbers.
    for key, label in [('nav_usd',r'NAV'), ('aum_usd',r'(?:Net assets|Total net assets)'),
                       ('closing_market_price_usd',r'Closing market price')]:
        observations = {}
        pattern = r'\b'+label+r'\s*(?:\((\d{1,2}/\d{1,2}/\d{4})\))?\s*[:]?\s*\$\s*([\d,]+(?:\.\d+)?)\s*([MB])?\b'
        for block in blocks:
            for m in re.finditer(pattern, block, re.I):
                val = float(m.group(2).replace(',','')) * {'M':1e6,'B':1e9}.get((m.group(3) or '').upper(),1)
                day = us_date(m.group(1))
                if val > 0 and (not m.group(1) or day):
                    observations.setdefault(day or '', set()).add(val)
        if observations:
            latest = max(observations)
            if len(observations[latest]) == 1:
                out['official_metrics'][key] = {'value':observations[latest].pop(),'as_of':latest or None,
                                               'date_state':'issuer_published' if latest else 'not_published'}
    if out['official_metrics']:
        out['official_data_state']='dated_issuer_data' if any(r.get('as_of') for r in out['official_metrics'].values()) else 'values_without_verified_as_of'
    return out
