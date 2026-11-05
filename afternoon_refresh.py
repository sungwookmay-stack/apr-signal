#!/usr/bin/env python3
"""APR SIGNAL afternoon close-price technical + local-news refresh.

Runs at 16:00 KST. No Scrape.do or API.SH calls and no FX/Customs refresh.
All new technical indicators use actual publicly fetched daily OHLCV bars.
The dashboard always displays the last verified stock/indicator date.
"""
from __future__ import annotations

import datetime as dt
import json
from pathlib import Path

import build_data
import update_data


def _bootstrap_previous(root: Path):
    path = root / 'bootstrap.js'
    try:
        txt = path.read_text(encoding='utf-8')
        prefix = 'window.APR_BOOTSTRAP = '
        if txt.startswith(prefix):
            existing = json.loads(txt[len(prefix):].strip().removesuffix(';'))
            if isinstance(existing, dict):
                return existing
    except (OSError, ValueError, TypeError):
        pass
    return {
        'kbty': build_data.read_json(root / 'kbty.json', {}),
        'demand': build_data.read_json(root / 'demand.json', {}),
    }


def refresh():
    root = build_data.DATA
    root.mkdir(parents=True, exist_ok=True)
    before = build_data.read_json(root / 'status.json', {})
    if not isinstance(before, dict):
        before = {}
    # collect_market calculates BB, RSI, MACD, Ichimoku, moving averages and ATR
    # from updated actual daily OHLCV, preserving earlier observations on failure.
    market, technical = build_data.collect_market(
        refresh_fx=False, refresh_freight=False)
    # Free Google News RSS + bounded free headline translations only.
    news = build_data.collect_news()

    now = dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    stock_asof = market.get('meta', {}).get('stock_last')
    tech_asof = technical.get('last', {}).get('date')
    kst_day = update_data.iso_today_kr().date().isoformat()
    status = dict(before)
    status.update({
        'generated_at_utc': now,
        'timezone': 'Asia/Seoul',
        'price_last': stock_asof,
        'price_coverage_start': market.get('meta', {}).get('coverage_start'),
        'fx_last': market.get('meta', {}).get('usd_fx_last'),
        'technical_last': tech_asof,
        'technical_ohlc_days': technical.get('valid_high_low', 0),
        'news_count': len(news.get('items', [])),
        'afternoon_updated_at_utc': now,
        'afternoon_price_date': stock_asof,
        'afternoon_verified_same_day': bool(
            stock_asof and tech_asof and stock_asof == tech_asof == kst_day),
        'afternoon_note': (
            '공개 일봉 기준 당일 장마감 자료 확인'
            if stock_asof == tech_asof == kst_day else
            '당일 종가 미확인 또는 휴장: 마지막 확인 거래일의 지표만 표시'
        ),
    })
    old_errors = status.get('errors', [])
    if not isinstance(old_errors, list):
        old_errors = []
    stock_errors = market.get('meta', {}).get('errors', [])
    errors = list(old_errors)
    for item in (stock_errors if isinstance(stock_errors, list) else []):
        if item not in errors:
            errors.append(item)
    for item in build_data.errors:
        if item not in errors:
            errors.append(item)
    status['errors'] = errors[-20:]
    build_data.save('status.json', status)

    # In addition to JSON endpoints, update the static bootstrap fallback.
    # Preserve morning-only demand, ETF, retailer and logistics observations.
    payload = _bootstrap_previous(root)
    payload.update({
        'market': market,
        'technical': technical,
        'news': news,
        'status': status,
    })
    (root / 'bootstrap.js').write_text(
        'window.APR_BOOTSTRAP = ' +
        json.dumps(payload, ensure_ascii=False, separators=(',', ':')) +
        ';\n', encoding='utf-8'
    )
    result = {
        'mode': 'afternoon_free_price_technical_and_news',
        'updated_at_utc': now,
        'stock_date': stock_asof,
        'technical_date': tech_asof,
        'same_day_stock_confirmed': status['afternoon_verified_same_day'],
        'news_count': status['news_count'],
        'amazon_trends_api_calls': 0,
        'fx_freight_refresh_calls': 0,
    }
    print(json.dumps(result, ensure_ascii=False))
    return result


if __name__ == '__main__':
    refresh()
