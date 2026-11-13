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


# Current issuer HTML publishes dated metrics and complete, dated holdings tables.
# No browser cookies, hidden endpoint, index weights or fetch-time dates are used.
from html.parser import HTMLParser

class _Table(HTMLParser):
    def __init__(self):
        super().__init__(); self.rows=[]; self.row=[]; self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag=='tr': self.row=[]
        if tag in ('th','td'): self.cell=[]
    def handle_data(self,s):
        if self.cell is not None:self.cell.append(s)
    def handle_endtag(self,tag):
        if tag in ('td','th') and self.cell is not None:
            self.row.append(' '.join(''.join(self.cell).split()));self.cell=None
        if tag=='tr' and self.row:self.rows.append(self.row)

def _date(s):
    try:return dt.datetime.strptime(s.strip(),'%m/%d/%Y').date().isoformat()
    except ValueError:return None

def _number(s):
    try:
        x=float(s.replace(',','').replace('$','').replace('%','').strip())
        return x if x>=0 and x<1e15 else None
    except (ValueError,AttributeError):return None

_legacy_parse=parse_official

def parse_official(document):
    out=_legacy_parse(document)
    out['holdings_snapshots']=[]
    if re.search(r'KBTY is now trading on NYSE Arca',document,re.I):
        out['status']='NYSE Arca 거래 중 (운용사 공식 확인)'
        out['trading_confirmed']=True
    facts=re.search(r'<section\b[^>]*id=[\"\']facts[\"\'][^>]*>(.*?)</section>',document,re.S|re.I)
    if facts:
        f=facts.group(1)
        def field(name):
            m=re.search(r'<span\b[^>]*data-field=[\"\']'+name+r'[\"\'][^>]*>([^<]*)</span>',f,re.I)
            return unescape(m.group(1)).strip() if m else ''
        for key,value,asof in [('nav_usd','nav','nav-asof'),('closing_market_price_usd','market-price','price-asof')]:
            n,d=_number(field(value)),_date(field(asof))
            if n and d:out['official_metrics'][key]={'value':n,'as_of':d,'date_state':'verified_issuer_date'}
        if any(x.get('as_of') for x in out['official_metrics'].values()):out['official_data_state']='dated_official_values'
    for table in re.findall(r'<table\b[^>]*>.*?</table>',document,re.S|re.I):
        cap=re.search(r'<caption\b[^>]*>(.*?)</caption>',table,re.S|re.I)
        if not cap:continue
        ct=re.sub('<[^>]+>',' ',cap.group(1))
        d=re.search(r'KBTY holdings as of (\d{2}/\d{2}/\d{4})',ct,re.I)
        expected=re.search(r'show all (\d+)',ct,re.I)
        if not d or not _date(d.group(1)):continue
        parser=_Table();parser.feed(table)
        if not parser.rows or parser.rows[0]!=['Net Assets %','Ticker','Name','Description','Market Price ($)','Shares Held','Market Value ($)','CUSIP']:continue
        rows=[]
        for cells in parser.rows[1:]:
            if len(cells)!=8:break
            weight,price,shares,value=[_number(cells[i]) for i in (0,4,5,6)]
            if None in (weight,price,shares,value) or weight>100:break
            rows.append({'as_of':_date(d.group(1)),'ticker':cells[1],'name':cells[2],
             'description':cells[3],'weight_pct':weight,'shares':shares,'market_price_usd':price,
             'market_value_usd':value,'cusip':cells[7],'source_url':'https://www.gafunds.com/kbty/'})
        if not expected or len(rows)!=int(expected.group(1)) or len(set(r['ticker'] for r in rows))!=len(rows) or not 99.5<=sum(r['weight_pct'] for r in rows)<=100.5:continue
        out['holdings_snapshots'].append({'as_of':rows[0]['as_of'],'holdings':rows,'complete':True})
    if out['holdings_snapshots']:
        out['holdings_snapshots'].sort(key=lambda x:x['as_of'])
        out['holdings_publication_state']='complete_dated_issuer_table'
    return out

def apply_official(state, parsed):
    """Merge only dated issuer observations; never regress on a stale page."""
    hist={x['as_of']:x for x in state.get('holdings_history',[]) if x.get('as_of')}
    hist.update({x['as_of']:x for x in parsed.get('holdings_snapshots',[])})
    state['holdings_history']=[hist[d] for d in sorted(hist)]
    if hist:
        last=state['holdings_history'][-1]
        state['holdings']=last['holdings'];state['holdings_as_of']=last['as_of']
        state['holdings_publication_state']='complete_dated_issuer_table'
    navs={x['date']:x for x in state.get('nav_history',[]) if x.get('date')}
    nav=parsed.get('official_metrics',{}).get('nav_usd',{})
    if nav.get('as_of') and nav.get('value'):
        navs[nav['as_of']]={'date':nav['as_of'],'nav_usd':nav['value'],'source_url':'https://www.gafunds.com/kbty/'}
    state['nav_history']=[navs[d] for d in sorted(navs)]
    if navs:
        last=state['nav_history'][-1];state['nav_usd']=last['nav_usd'];state['nav_as_of']=last['date']
    price=parsed.get('official_metrics',{}).get('closing_market_price_usd',{})
    if price.get('as_of') and price.get('value') and price['as_of']>=(state.get('official_price_as_of') or ''):
        state['official_price_usd']=price['value'];state['official_price_as_of']=price['as_of']
