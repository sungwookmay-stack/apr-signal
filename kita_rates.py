#!/usr/bin/env python3
"""US West/East KITA RADIS reference ocean rates (free public sources).

West (Busan->Long Beach) comes from the primary KITA public rate table.
East (Busan->New York) uses KITA official monthly bulletin pages when
available. The later September/October 2026 East FEU figures are explicitly
labelled SECONDARY KITA-citing data, NOT KITA-directly-verified figures.
No extrapolation, no filled missing months, no assumed TEU=FEU conversion.
"""
from __future__ import annotations

import datetime as dt
import html as html_lib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib import request

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'data' / 'kita_rates.json'
SEA_URL = 'https://www.kita.net/shippers/logisticsFare/logisticsSeaFare.do'
AIR_URL = 'https://www.kita.net/shippers/logisticsFare/logisticsAirFare.do'
SECONDARY_URL = 'https://logisight.net/rates'
SECONDARY_LIVE_URL = 'https://logisight.net/dashboard'

WEST_HISTORY = [
    ('2026-01', 2500, 3100), ('2026-02', 1450, 1850),
    ('2026-03', 2300, 2860), ('2026-04', 2900, 3100),
    ('2026-05', 2400, 2900), ('2026-06', 3960, 4950),
    ('2026-07', 6000, 7550), ('2026-08', 6200, 7600),
    ('2026-09', 6400, 7900), ('2026-10', 6700, 8500),
]
# Explicitly verified KITA article URLs and the NEW YORK rate printed there.
# Only these dated months may be tagged KITA_OFFICIAL_BULLETIN.
EAST_OFFICIAL = [
    ('2026-04', 3100, 4000,
     'https://www.kita.net/shippers/board/courseTrendView.do?dataSeq=3375&morgueCode=8'),
    ('2026-06', 5000, 6150,
     'https://www.kita.net/shippers/board/courseTrendView.do?dataSeq=3390&morgueCode=8'),
    ('2026-07', 7500, 9500,
     'https://www.kita.net/shippers/board/courseTrendView.do?dataSeq=3394&morgueCode=8'),
]
# Separate third-party monitoring cites KITA monthly lane figures. Keep weaker
# provenance and don't fabricate the unavailable TEU values.
EAST_SECONDARY = [
    ('2026-09', None, 11300),
    ('2026-10', None, 11900),
]


class TableRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() == 'tr':
            self.row = []
        if tag.lower() in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        if tag.lower() in ('td', 'th') and self.cell is not None and self.row is not None:
            self.row.append(re.sub(r'\s+', ' ', ' '.join(self.cell)).strip())
            self.cell = None
        if tag.lower() == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def _number(text):
    m = re.match(r'^\s*([0-9][0-9,]*(?:\.[0-9]+)?)', str(text))
    return float(m.group(1).replace(',', '')) if m else None


def _rate_record(month, destination, teu, feu, url, source_type, published=None):
    if not re.fullmatch(r'20\d{2}-(0[1-9]|1[0-2])', month):
        return None
    if destination not in ('Long Beach', 'New York'):
        return None
    if feu is None or not 100 <= float(feu) <= 40000:
        return None
    if teu is not None and not 100 <= float(teu) <= 30000:
        return None
    return {
        'month': month, 'origin': 'Busan', 'destination': destination,
        'region': '미국 서안' if destination == 'Long Beach' else '미국 동안',
        'teu_usd': int(teu) if teu is not None else None,
        'feu_usd': int(feu),
        'source_url': url, 'source_type': source_type,
        'verified_on': published
    }


def parse_sea_rates(html):
    """Parse live public KITA detailed table, keeping only supported ports."""
    parser = TableRows()
    parser.feed(html)
    out = []
    for row in parser.rows:
        if len(row) < 6:
            continue
        origin, dest = row[0].strip(), row[1].strip()
        if not re.fullmatch(r'Busan|부산', origin, flags=re.I):
            continue
        mapping = {'Long Beach':'Long Beach', '롱비치':'Long Beach',
                   'New York':'New York', '뉴욕':'New York'}
        destination = mapping.get(dest)
        if not destination:
            continue
        if not re.fullmatch(r'20\d{2}', row[2]) or not re.fullmatch(
                r'0?[1-9]|1[0-2]', row[3]):
            continue
        month = f'{int(row[2]):04d}-{int(row[3]):02d}'
        teu, feu = _number(row[4]), _number(row[6] if len(row) >= 8 else row[5])
        rec = _rate_record(
            month, destination, teu, feu, SEA_URL, 'KITA_RADIS_PUBLIC_HTML')
        if rec:
            out.append(rec)
    return list({(r['month'], r['destination']): r for r in out}.values())


def parse_sea_bulletin(html, source_url):
    """Parse dated official KITA maritime export notice for US East/West.

    Date and maritime context are checked in the heading before row parsing;
    empty or N/S rates cannot become a fake zero-dollar quote.
    """
    plain = html_lib.unescape(re.sub(r'(?s)<[^>]*>', ' ', html))
    plain = re.sub(r'\s+', ' ', plain)
    match = re.search(
        r'(20\d{2})\s*년\s*(0?[1-9]|1[0-2])\s*월\s*RADIS\s*참고\s*운임\s*안내\s*\(\s*해상\s*수출\s*운임\s*\)',
        plain)
    if not match:
        return []
    month = f'{int(match.group(1)):04d}-{int(match.group(2)):02d}'
    parser = TableRows()
    parser.feed(html)
    result = []
    for row in parser.rows:
        if len(row) < 3:
            continue
        dest = row[0].strip()
        mapping = {'Long Beach': 'Long Beach', 'New York': 'New York'}
        city = mapping.get(dest)
        if not city:
            continue
        teu, feu = _number(row[1]), _number(row[2])
        rec = _rate_record(month, city, teu, feu, source_url,
                           'KITA_RADIS_OFFICIAL_BULLETIN')
        if rec:
            result.append(rec)
    return result



def parse_secondary_east(html):
    """Best-effort parse of labelled KITA *citation* from a third-party page.

    This is strictly lower-provenance than the KITA official data. Keep only
    a dated New York FEU reference; TEU is unknown, never derived from FEU.
    """
    cleaned=html_lib.unescape(re.sub(
        r'(?is)<script\b[^>]*>.*?</script>|<style\b[^>]*>.*?</style>',
        ' ', html))
    plain=re.sub(r'\s+', ' ', re.sub(r'(?s)<[^>]*>', ' ', cleaned))
    if 'KITA' not in plain or '해상' not in plain:
        return None
    match=re.search(
        r'부산\s*→\s*뉴욕\s*\$\s*([\d,]+)\s*/\s*FEU'
        r'.{0,100}?(20\d{2}-(?:0[1-9]|1[0-2]))',
        plain)
    if not match:
        return None
    feu=int(match.group(1).replace(',',''))
    month=match.group(2)
    if month>dt.date.today().strftime('%Y-%m'):
        return None
    return _rate_record(month,'New York',None,feu,SECONDARY_LIVE_URL,
        'KITA_RADIS_SECONDARY_REPORT_UNCONFIRMED_PRIMARY',
        dt.date.today().isoformat())

def _seed():
    west = [_rate_record(m,'Long Beach',teu,feu,SEA_URL,
                        'KITA_RADIS_VERIFIED_SNAPSHOT_2026-11-09','2026-11-09')
            for m,teu,feu in WEST_HISTORY]
    east = [_rate_record(m,'New York',teu,feu,url,
                        'KITA_RADIS_OFFICIAL_BULLETIN','2026-11-09')
            for m,teu,feu,url in EAST_OFFICIAL]
    later = [_rate_record(m,'New York',teu,feu,SECONDARY_URL,
             'KITA_RADIS_SECONDARY_REPORT_UNCONFIRMED_PRIMARY','2026-11-09')
             for m,teu,feu in EAST_SECONDARY]
    return [r for r in west+east+later if r]


def _fetch(url, timeout=14):
    req = request.Request(
        url, headers={'User-Agent':'Mozilla/5.0 APR-research/1.0',
                      'Accept':'text/html,application/xhtml+xml'})
    with request.urlopen(req, timeout=timeout) as r:
        return r.read().decode('utf-8',errors='replace')


def _sort_key(row):
    # Keep Long Beach last for compatibility with the initial single-route
    # data consumer; charting should always filter destination explicitly.
    return (row['month'], 1 if row['destination']=='Long Beach' else 0)


def update(output=TARGET, fetch_html=None, fetch_bulletin=None,
           fetch_secondary=None):
    """Fetch latest KITA public table + dated East official bulletins as needed.

    Optional, separately sourced 2026 Sep/Oct East figures remain clearly
    labelled SECONDARY, even if the primary default city page loads normally.
    """
    output = Path(output)
    try:
        old = json.loads(output.read_text(encoding='utf-8'))
    except (OSError,ValueError,TypeError):
        old = {}
    previous = old.get('sea_routes',[]) if isinstance(old,dict) else []
    rows = {(r['month'],r['destination']): r for r in _seed()}
    for r in previous:
        if (r.get('month') and r.get('destination') in ('New York','Long Beach')
                and r.get('source_url') and r.get('feu_usd')):
            key=(r['month'],r['destination'])
            # Never replace an official source with a lower-confidence snapshot.
            if (rows.get(key,{}).get('source_type','').startswith('KITA_RADIS_OFFICIAL_')
                and not r.get('source_type','').startswith('KITA_RADIS_OFFICIAL_')):
                continue
            rows[key]=r
    checked = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    errors=[]
    west_access=False
    live_east=False
    live_collection = fetch_html is None
    fetch_html=fetch_html or (lambda: _fetch(SEA_URL))
    try:
        parsed=parse_sea_rates(fetch_html())
        if not parsed:
            raise ValueError('KITA detailed table empty or access limited')
        for r in parsed:
            if r['month']<=dt.date.today().strftime('%Y-%m'):
                rows[(r['month'],r['destination'])]=r
                if r['destination']=='Long Beach':
                    west_access=True
                else:
                    live_east=True
    except Exception as exc:
        errors.append('KITA 기본 조회: '+type(exc).__name__+': '+str(exc)[:90])
    fetch_bulletin=fetch_bulletin or _fetch
    official_backfilled=0
    for month,teu,feu,url in EAST_OFFICIAL:
        key=(month,'New York')
        # Do not re-fetch immutable bulletins once already sourced from KITA.
        if rows.get(key,{}).get('source_type')=='KITA_RADIS_OFFICIAL_BULLETIN':
            continue
        try:
            parsed=parse_sea_bulletin(fetch_bulletin(url),url)
            for r in parsed:
                if r['month']==month:
                    rows[(r['month'],r['destination'])]=r
                    official_backfilled+=1
        except Exception as exc:
            errors.append(month+' 공식 보도자료: '+type(exc).__name__)
    # The optional third-party reference is never presented as a KITA
    # confirmed market quote. It gives a new-month signal while the KITA
    # direct New York destination selector is not supported by this scraper.
    secondary_ok=None
    if fetch_secondary is None and live_collection:
        fetch_secondary=lambda: _fetch(SECONDARY_LIVE_URL)
    if fetch_secondary is not None:
        try:
            second=parse_secondary_east(fetch_secondary())
            if not second:
                raise ValueError('Dated KITA-citing New York FEU row absent')
            key=(second['month'],'New York')
            existing=rows.get(key,{})
            if not (existing.get('source_type') in
                    ('KITA_RADIS_OFFICIAL_BULLETIN','KITA_RADIS_PUBLIC_HTML')):
                rows[key]=second
            secondary_ok=True
        except Exception as exc:
            secondary_ok=False
            errors.append('미 동안 2차 공개자료: '+type(exc).__name__)
    records=sorted(rows.values(),key=_sort_key)
    west=[r for r in records if r['destination']=='Long Beach']
    east=[r for r in records if r['destination']=='New York']
    east_latest=east[-1] if east else {}
    west_latest=west[-1] if west else {}
    result={
        'provider':'한국무역협회 KITA RADIS',
        'sea_source_url':SEA_URL,'air_source_url':AIR_URL,
        'method':'협력 포워더 조사 시장 참고운임 · USD/TEU·FEU (APR 계약운임 아님)',
        'source_scope':'미 서안 부산→롱비치 / 미 동안 부산→뉴욕 대표. 항만별 실제 계약운임·해상물량 배분 아님.',
        'latest_month':max((r['month'] for r in records),default=None),
        'latest_access_checked_at_utc':checked,
        'latest_access_ok':west_access,
        'west_latest_month':west_latest.get('month'),
        'east_latest_month':east_latest.get('month'),
        'east_latest_source':east_latest.get('source_type'),
        'east_latest_primary_verified':bool(
            east_latest.get('source_type','').startswith('KITA_RADIS_OFFICIAL_') or
            east_latest.get('source_type')=='KITA_RADIS_PUBLIC_HTML'),
        'east_auto_updated':live_east or official_backfilled>0 or secondary_ok is True,
        'east_secondary_access_ok':secondary_ok,
        'east_secondary_url':SECONDARY_LIVE_URL,
        'east_note':'최근 2026-09/10 뉴욕값은 KITA 인용 제3자 2차 출처이며 공식 항로별 조회 대조 전. 공란은 보간하지 않음.',
        'air_routes':old.get('air_routes',[]) if isinstance(old,dict) else [],
        'air_status':'KITA 항공 수출 기본 선택은 실측 확인 전 (기존 정책 유지)',
        'sea_routes':records,'errors':errors
    }
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'west_month':result['west_latest_month'],
                      'east_month':result['east_latest_month'],
                      'west_access':west_access,
                      'east_primary_verified':result['east_latest_primary_verified'],
                      'routes':len(records),'errors':errors},ensure_ascii=False))
    return result


if __name__=='__main__':
    update()
