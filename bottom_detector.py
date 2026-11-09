"""APR bottom formation monitor using confirmed historical price/volume evidence.

This is a lagging *classification*, NOT a probability, target-price forecast
or guarantee of the ultimate low. Only OHLCV and technical indicators known
as of the supplied last session are consulted. A swing low at index i is
considered confirmed only after THREE subsequent trading sessions.
Sources: Fidelity technical-indicator guide, StockCharts bullish divergence
guidance, and CMT Association's capitulation/divergence/confirmation framework.
Weights/thresholds below are engineering heuristics, not validated hit rates.
"""
from __future__ import annotations
from math import isfinite

SOURCE_URLS = [
    "https://www.fidelity.com/learning-center/trading-investing/technical-analysis/what-is-technical-analysis",
    "https://help.stockcharts.com/scanning-and-alerts/scan-writing-resource-center/scanning-case-studies/scanning-for-divergences",
    "https://content.cmtassociation.org/a/spotting-a-market-bottom"
]


def _float(x):
    if isinstance(x, (int, float)) and isfinite(x):
        return float(x)
    return None


def _round(x, digits=2):
    return round(x, digits) if x is not None else None


def confirmed_lows(rows, left=3, right=3):
    """Return only right-confirmed local swing lows; never provisional lows.

    Rows may include 'low' and 'rsi14'. The confirmation date is the row at
    i+right; signals on that day may not retrospectively appear at i.
    """
    out = []
    for i in range(left, len(rows)-right):
        low = _float(rows[i].get('low'))
        if low is None or low <= 0:
            continue
        before = [_float(r.get('low')) for r in rows[i-left:i]]
        after = [_float(r.get('low')) for r in rows[i+1:i+1+right]]
        if (all(v is not None for v in before + after)
                and low <= min(before) and low < min(after)):
            out.append({
                'index': i, 'date': rows[i]['date'], 'low': round(low),
                'rsi14': _float(rows[i].get('rsi14')),
                'confirmed_on': rows[i+right]['date']
            })
    return out


def analyze(ohlcv, indicators):
    """Stage and transparent evidence at the last observed trading session."""
    if not ohlcv or not indicators or len(indicators) < 65:
        return {
            'date': indicators[-1].get('date') if indicators else None,
            'stage': '판단 보류 · 최소 65거래일 OHLCV 필요',
            'kind': 'unknown', 'score': None, 'max_score': 10,
            'checks': [], 'data_ready': False, 'not_prediction': True,
            'sources': SOURCE_URLS
        }
    by_date = {r.get('date'): r for r in ohlcv}
    rows = []
    for item in indicators:
        row = by_date.get(item.get('date'), {})
        low = _float(row.get('low_krw'))
        high = _float(row.get('high_krw'))
        close = _float(item.get('close'))
        volume = _float(row.get('volume'))
        if low is None or high is None or close is None or low > high or not(low <= close <= high):
            return {
                'date': indicators[-1].get('date'),
                'stage': '판단 보류 · 가격 고가·저가 정합성 오류',
                'kind': 'unknown', 'score': None, 'max_score': 10,
                'checks': [], 'data_ready': False, 'not_prediction': True,
                'sources': SOURCE_URLS
            }
        rows.append({**item, 'low': low, 'high': high, 'volume': volume})
    latest = rows[-1]
    close = latest['close']
    rsi = _float(latest.get('rsi14'))
    macdh = _float(latest.get('macd_hist'))
    ma5 = _float(latest.get('ma5'))
    ma20 = _float(latest.get('ma20'))
    ma60 = _float(latest.get('ma60'))
    atr = _float(latest.get('atr14'))
    vratio = _float(latest.get('volume_ratio20'))
    if any(v is None for v in (rsi, macdh, ma5, ma20, ma60, atr)):
        return {
            'date': latest['date'],
            'stage': '판단 보류 · 필수 RSI·MACD·이평선·ATR 누락',
            'kind': 'unknown', 'score': None, 'max_score': 10,
            'checks': [], 'data_ready': False, 'not_prediction': True,
            'sources': SOURCE_URLS
        }

    def observed_score(idx):
        if idx < 20:
            return None
        vols = [r['volume'] for r in rows[idx-20:idx]
                if r['volume'] is not None and r['volume'] > 0]
        if len(vols) != 20:
            return None
        v = rows[idx]['volume']
        return v/(sum(vols)/len(vols)) if v else None

    # Washout must happen before the claimed low. It does NOT prove a bottom.
    capitulations = []
    for i in range(max(60, len(rows)-20), len(rows)):
        prior_top = max(r['close'] for r in rows[i-59:i+1])
        drop = (rows[i]['close'] / prior_top-1)*100 if prior_top else 0
        volratio = observed_score(i)
        move = (rows[i]['close']/rows[i-1]['close']-1)*100
        if (drop <= -18 and volratio is not None and volratio >= 1.8
                and move <= -4):
            capitulations.append({
                'date': rows[i]['date'], 'volume_multiple': _round(volratio, 1),
                'drawdown_from_60d_top_pct': _round(drop, 1)
            })
    washout = capitulations[-1] if capitulations else None

    pivots = confirmed_lows(rows)
    recent_pivots = [p for p in pivots if len(rows)-1-p['index'] <= 55]
    p1, p2 = (recent_pivots[-2], recent_pivots[-1]) if len(recent_pivots) >= 2 else (None, None)
    spacing = (p2['index']-p1['index']) if p1 and p2 else 0
    divergence = bool(
        spacing >= 5 and p1['rsi14'] is not None and p2['rsi14'] is not None
        and p2['low'] <= p1['low']*0.995
        and p2['rsi14'] >= p1['rsi14']+3
    )
    retest = bool(
        spacing >= 5 and p1['rsi14'] is not None and p2['rsi14'] is not None
        and p2['low'] >= p1['low']*0.975
        and p2['low'] <= p1['low']*1.06
        and p2['rsi14'] >= p1['rsi14']-3
    )
    improving_hist = bool(
        len(rows) >= 3 and
        all(_float(rows[i].get('macd_hist')) is not None for i in (-3, -2, -1))
        and rows[-3]['macd_hist'] < rows[-2]['macd_hist'] < macdh
    )
    recovered_rsi = bool(rsi >= 40 and rsi > (rows[-2].get('rsi14') or -1))
    ma5_reclaim = close >= ma5
    above_ma20_3 = bool(len(rows) >= 3 and all(
        r.get('ma20') is not None and r['close'] >= r['ma20']
        for r in rows[-3:]
    ))
    prior10_high_close = max(r['close'] for r in rows[-11:-1])
    resistance_break = bool(
        close > prior10_high_close and vratio is not None and vratio >= 1.25
    )
    prior20_min = min(r['low'] for r in rows[-21:-1])
    breakdown = close < prior20_min * 0.99
    drawdown60 = (close / max(r['close'] for r in rows[-60:])-1)*100

    checks = []
    score = 0
    def add(name, ok, points, explanation):
        nonlocal score
        if ok:
            score += points
        checks.append({
            'name': name, 'passed': bool(ok), 'points': points if ok else 0,
            'max_points': points, 'detail': explanation
        })
    add('투매·거래량 급증 확인', bool(washout), 1,
        ('마지막 투매 '+washout['date']+', 거래량 '+str(washout['volume_multiple'])
          +'배 · 과매도는 단독 바닥 신호 아님') if washout
        else '최근 20거래일 내 거래량 1.8배 이상·당일 -4% 이하 등 투매 조건 미충족')
    add('가격·RSI 상승 다이버전스', divergence, 2,
        (f"가격 저점 {p1['low']:,}→{p2['low']:,}원, RSI {p1['rsi14']:.1f}→{p2['rsi14']:.1f}"
         if divergence else '확정된 두 저점에서 저가 하락·RSI 저점 상승을 동시 확인하지 못함'))
    add('지지선 재시험 또는 높아진 저점', retest, 2,
        (f"확정 저점 {p1['low']:,}→{p2['low']:,}원 · 새 저점은 3거래일 후 확정"
         if retest else '저점이 높아지는 구조는 아직 확인 전 (3일 우측 확인 필요)'))
    add('MACD 히스토그램 연속 개선', improving_hist, 1,
        f"최근 MACD 히스토그램 {macdh:,.0f} · 3개 관측값 연속 상승 여부")
    add('RSI 40 이상으로 복귀·상승', recovered_rsi, 1,
        f"RSI(14) {rsi:.1f} · 30 미만은 과매도일 뿐 바닥 아님")
    add('5일 이동평균 회복', ma5_reclaim, 1,
        f"종가 {close:,.0f}원 / 5일선 {ma5:,.0f}원")
    add('20일선 3거래일 유지', above_ma20_3, 1,
        f"현재 20일선 {ma20:,.0f}원 · 단일 장중 돌파로 미확정")
    add('10일 전고점·거래량 돌파', resistance_break, 1,
        f"이전 10일 최고종가 {prior10_high_close:,.0f}원 / 거래량배수 "+
        (f"{vratio:.2f}" if vratio is not None else '미확인'))

    if breakdown:
        stage = '저점 재이탈 경계 · 바닥 미확인'
        kind = 'risk'
    elif retest and (divergence or recovered_rsi) and above_ma20_3 and resistance_break and score >= 7:
        stage = '추세 반전 1차 확인 · 재시험 필요'
        kind = 'confirmation'
    elif (retest or divergence) and improving_hist and (ma5_reclaim or recovered_rsi):
        stage = '바닥 형성 가능성 · 추가 확인 필요'
        kind = 'building'
    elif washout and improving_hist:
        stage = '투매 후 반등 탐색 · 바닥 미확인'
        kind = 'early'
    elif washout:
        stage = '투매 관찰 · 바닥 미확인'
        kind = 'early'
    else:
        stage = '하락 추세 / 바닥 신호 미확인'
        kind = 'risk' if close < ma20 and close < ma60 else 'unknown'

    min20 = min((r['low'], r['date']) for r in rows[-20:])
    return {
        'date': latest['date'],
        'stage': stage, 'kind': kind, 'score': score, 'max_score': 10,
        'checks': checks, 'data_ready': True,
        'washout': washout,
        'latest_confirmed_swing_low': pivots[-1] if pivots else None,
        'recent_two_confirmed_lows': [p1, p2] if p1 and p2 else [],
        'bullish_rsi_divergence': divergence,
        'retest_confirmed': retest,
        'breakdown': breakdown,
        'reference': {
            'recent_20d_low': round(min20[0]),
            'recent_20d_low_date': min20[1],
            'prev_20d_low': round(prior20_min),
            'ma5': round(ma5), 'ma20': round(ma20),
            'ma60': round(ma60), 'prior_10d_high_close': round(prior10_high_close),
            'atr14': round(atr), 'drawdown_60d_pct': _round(drawdown60, 1),
        },
        'note': ('과매도·투매는 저점 후보에 불과합니다. RSI 상승 다이버전스/저점 재확인'
                 ' 이후 5·20일선 회복과 거래량 동반 전고점 돌파를 구분해 판정합니다.'
                 ' 단계별 규칙은 과거 수익률로 검증된 승률 또는 가격 예측이 아닙니다.'),
        'not_prediction': True, 'sources': SOURCE_URLS
    }
