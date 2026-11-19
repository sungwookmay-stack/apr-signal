"""Normalize display provenance of saved observations without recollecting data."""
from datetime import date
import json
from pathlib import Path

KBTY_ISSUER = 'https://www.gafunds.com/kbty/'


def _day(value):
    try:
        return value == date.fromisoformat(value).isoformat()
    except (ValueError, TypeError):
        return False


def _dated_number(row, key, date_key):
    if not isinstance(row, dict) or not _day(row.get(date_key)):
        return False
    value = row.get(key)
    return type(value) in (int, float) and 0 < value < float('inf')


def kbty_source_note(data):
    """Describe saved evidence field by field, never from its fetch timestamp."""
    lines = []
    source = data.get('price_source')
    price_valid = _dated_number(data, 'latest_price_usd', 'price_date')
    official_metrics = data.get('official_metrics')
    official_metrics = official_metrics if isinstance(official_metrics, dict) else {}
    quote = official_metrics.get('closing_market_price_usd')
    if (price_valid and data.get('official_url') == KBTY_ISSUER
            and _dated_number(quote, 'value', 'as_of')
            and quote['as_of'] == data['price_date'] and quote['value'] == data['latest_price_usd']):
        lines.append('가격: Guinness Atkinson 운용사 공식 종가')
    elif price_valid and isinstance(source, str) and 'Yahoo Finance' in source:
        lines.append('가격: Yahoo Finance 비공식 일별시세')
    elif price_valid:
        lines.append('가격: 저장된 일별시세의 개별 출처 참조')
    else:
        lines.append('가격: 확인 자료 없음 (Yahoo Finance 비공식 일별시세는 보조 출처)')

    nav = official_metrics.get('nav_usd')
    if (data.get('official_url') == KBTY_ISSUER
            and _dated_number(nav, 'value', 'as_of')
            and nav['as_of'] == data.get('nav_as_of') and nav['value'] == data.get('nav_usd')):
        lines.append('NAV: 운용사 공식 순자산가치')
    elif data.get('nav_usd') is not None:
        lines.append('NAV: 저장값의 개별 출처 참조')

    rows = data.get('holdings')
    rows = rows if isinstance(rows, list) else []
    if any(isinstance(row, dict) and row.get('source_url') == KBTY_ISSUER
           and row.get('ticker') in ('A278470','278470','278470.KS','278470 KS')
           and row.get('as_of') == data.get('apr_holding_as_of')
           and _dated_number(row, 'shares', 'as_of')
           and row['shares'] == data.get('apr_shares')
           and row.get('weight_pct') == data.get('apr_weight_pct') for row in rows):
        lines.append('APR 비중·보유주식수: 운용사 날짜별 보유 내역')
    elif data.get('apr_holding_as_of'):
        lines.append('APR 비중·보유주식수: 개별 보유 내역의 출처 참조')

    if data.get('aum_usd') is None:
        lines.append('AUM: 확인 자료 없음')
    else:
        lines.append('AUM: 저장된 수치의 개별 출처 참조')
    lines.append('미확인 항목은 표시하지 않음')
    return '. '.join(lines) + '.'


def normalize_saved_sources(root):
    root = Path(root)
    for name in ('flows', 'kbty'):
        path = root / (name + '.json')
        try:
            data = json.loads(path.read_text(encoding='utf-8'))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict):
            continue
        if name == 'kbty':
            note = kbty_source_note(data)
            if data.get('source_note') == note:
                continue
            data['source_note'] = note
        else:
            data['source_scope'] = '투자자 수급·공매도·대차는 별도 자료이며 각 관측의 source/source_url 및 기준일을 따름'
            status = data.setdefault('data_status', {})
            latest = data.get('latest_daily') or {}
            loan = (data.get('lending') or {}).get('latest') or {}
            status['primary_source'] = latest.get('source', '미수집')
            status['flow_source_url'] = latest.get('source_url')
            status['lending_source_url'] = loan.get('source_url')
            status['warning'] = ('KRX 범위와 NXT 포함 여부·거래시간 구분을 원천 자료와 대조. '
                                 '관측별 unit·amount_estimated로 실제 거래대금과 주수×종가 추정을 구분. '
                                 '연기금은 기관 합계의 부분집합')
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
