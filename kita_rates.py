#!/usr/bin/env python3
"""KITA RADIS route-level reference ocean rates (free public HTML).

KITA RADIS is a MONTHLY FIRST-WEEK MARKET REFERENCE (USD/TEU and USD/FEU),
not an APR contract, actual paid invoice or Korea Customs' monthly declared
transport cost. Air reference data require a separately verified selection.
Never fabricate missing routes/air prices or treat unannounced 0 as a rate.
"""
from __future__ import annotations
import datetime as dt
from html.parser import HTMLParser
import json
from pathlib import Path
import re
from urllib import request

ROOT = Path(__file__).resolve().parent
TARGET = ROOT / 'data' / 'kita_rates.json'
SEA_URL = 'https://www.kita.net/shippers/logisticsFare/logisticsSeaFare.do'
AIR_URL = 'https://www.kita.net/shippers/logisticsFare/logisticsAirFare.do'

# Source: official KITA sea-detail table for Busan -> Long Beach, checked
# 2026-11-09. First numbers are USD rates; site also shows month-to-month
# USD changes in adjacent columns/text. Not APR contracted cargo rates.
VERIFIED_SNAPSHOT = [
    ('2026-01', 2500, 3100), ('2026-02', 1450, 1850),
    ('2026-03', 2300, 2860), ('2026-04', 2900, 3100),
    ('2026-05', 2400, 2900), ('2026-06', 3960, 4950),
    ('2026-07', 6000, 7550), ('2026-08', 6200, 7600),
    ('2026-09', 6400, 7900), ('2026-10', 6700, 8500),
]


class TableRows(HTMLParser):
    def __init__(self):
        super().__init__()
        self.rows = []
        self.row = None
        self.cell = None

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag == 'tr':
            self.row = []
        if tag in ('td', 'th') and self.row is not None:
            self.cell = []

    def handle_data(self, data):
        if self.cell is not None:
            self.cell.append(data)

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in ('td', 'th') and self.cell is not None and self.row is not None:
            self.row.append(re.sub(r'\s+', ' ', ' '.join(self.cell)).strip())
            self.cell = None
        elif tag == 'tr' and self.row is not None:
            self.rows.append(self.row)
            self.row = None


def _number(text):
    m = re.match(r'^\s*([0-9][0-9,]*(?:\.[0-9]+)?)', str(text))
    return float(m.group(1).replace(',', '')) if m else None


def parse_sea_rates(html):
    """Read only verifiable route rows; exclude the second, change-only number."""
    parser = TableRows()
    parser.feed(html)
    out = []
    for row in parser.rows:
        if len(row) < 6:
            continue
        origin, dest = row[0].strip(), row[1].strip()
        if not re.fullmatch(r'Busan|부산', origin, flags=re.I):
            continue
        if not re.fullmatch(r'Long Beach|롱비치', dest, flags=re.I):
            # Do not mislabel other routes; add mapping when independently
            # verified and tested against their real source table.
            continue
        if not re.fullmatch(r'20\d{2}', row[2]) or not re.fullmatch(
                r'0?[1-9]|1[0-2]', row[3]):
            continue
        month = f'{int(row[2]):04d}-{int(row[3]):02d}'
        teu = _number(row[4])
        feu = _number(row[6] if len(row) >= 8 else row[5])
        if teu is None or feu is None or teu <= 0 or feu <= 0:
            continue
        if not (100 <= teu <= 30000 and 100 <= feu <= 40000):
            continue
        out.append({
            'month': month, 'origin': 'Busan', 'destination': 'Long Beach',
            'teu_usd': int(teu) if teu.is_integer() else teu,
            'feu_usd': int(feu) if feu.is_integer() else feu,
            'source_url': SEA_URL, 'source_type': 'KITA_RADIS_PUBLIC_HTML'
        })
    return list({r['month']: r for r in out}.values())


def _seed():
    return [{
        'month': month, 'origin': 'Busan', 'destination': 'Long Beach',
        'teu_usd': teu, 'feu_usd': feu, 'source_url': SEA_URL,
        'source_type': 'KITA_RADIS_VERIFIED_SNAPSHOT_2026-11-09',
        'verified_on': '2026-11-09'
    } for month, teu, feu in VERIFIED_SNAPSHOT]


def update(output=TARGET, fetch_html=None):
    """Preserve sourced history, try live HTML, expose collection failures."""
    output = Path(output)
    try:
        old = json.loads(output.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        old = {}
    prior = old.get('sea_routes', []) if isinstance(old, dict) else []
    rows = {r['month']: r for r in _seed()}
    for r in prior:
        if r.get('month') and r.get('source_url') == SEA_URL:
            rows[r['month']] = r
    check = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    errors = []
    fresh_count = 0
    if fetch_html is None:
        def fetch_html():
            req = request.Request(SEA_URL, headers={
                'User-Agent': 'Mozilla/5.0 APR-research/1.0',
                'Accept': 'text/html,application/xhtml+xml'
            })
            with request.urlopen(req, timeout=14) as resp:
                return resp.read().decode('utf-8', errors='replace')
    try:
        parsed = parse_sea_rates(fetch_html())
        if not parsed:
            raise ValueError('KITA HTML route table missing or access limited')
        for row in parsed:
            if row['month'] <= dt.datetime.now(dt.timezone.utc).strftime('%Y-%m'):
                rows[row['month']] = row
                fresh_count += 1
    except Exception as exc:
        errors.append(type(exc).__name__ + ': ' + str(exc)[:150])
    records = [rows[k] for k in sorted(rows)]
    result = {
        'provider': '한국무역협회 KITA RADIS',
        'sea_source_url': SEA_URL, 'air_source_url': AIR_URL,
        'method': '협력업체 조사 시장 참고운임·매월 첫째 주·USD/TEU 및 USD/FEU',
        'source_scope': '부산→롱비치 공개 기본 조회 항로만 확인. 기타 항로와 항공은 미확인.',
        'latest_month': records[-1]['month'] if records else None,
        'latest_access_checked_at_utc': check,
        'latest_access_ok': bool(fresh_count),
        'verified_snapshot_date': '2026-11-09',
        'air_routes': [],
        'air_status': '항공 공개 기본 조회는 결과 없음: 공란 유지',
        'sea_routes': records,
        'errors': errors
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                      encoding='utf-8')
    print(json.dumps({
        'kita_latest_month': result['latest_month'],
        'sea_records': len(records), 'fresh_rows': fresh_count,
        'access_ok': result['latest_access_ok'], 'errors': errors
    }, ensure_ascii=False))
    return result


if __name__ == '__main__':
    update()
