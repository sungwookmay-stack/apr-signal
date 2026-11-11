"""APR investor-flow research metrics, no invented observations.

KRX investor classification: financial investments / insurance / trusts /
private funds / banks / other finance / pensions = INSTITUTIONS total.
Pensions are a SUBSET and must never be added again to institution totals.
Volumes, short interest and stock lending have different definitions.
This module is deliberately source-agnostic and has no network I/O.
"""
from __future__ import annotations
from datetime import date, datetime, timezone
from math import isfinite

ACTORS = {
    'individual': '개인',
    'foreign': '외국인 합계',
    'institution': '기관 합계',
    'pension': '연기금 등 (기관 내 포함)',
}
WINDOWS = (5, 20, 60)


def num(x):
    return float(x) if isinstance(x, (int, float)) and isfinite(x) else None


def month_data(price_rows, flow_rows, actor, n):
    """Only count a complete run of n matching trading sessions."""
    recent = [x for x in price_rows if x.get('date')][-n:]
    if len(recent) != n:
        return None
    by_day = {x['date']: x for x in flow_rows if x.get('date')}
    dates = [x['date'] for x in recent]
    vals = [num(by_day.get(d, {}).get(actor)) for d in dates]
    if any(v is None for v in vals):
        return None
    # KRW not shares; positive = buys minus sells.
    proxy = sum((num(x.get('close_krw')) or 0) *
                (num(x.get('volume')) or 0) for x in recent)
    total = sum(vals)
    positive = sum(v > 0 for v in vals)
    streak = 0
    for v in vals[::-1]:
        if v <= 0:
            break
        streak += 1
    estimate_days=sum(bool(by_day[d].get('amount_estimated')) for d in dates)
    quantity_values=[num(by_day[d].get(actor+'_net_qty')) for d in dates]
    net_qty=round(sum(quantity_values)) if all(v is not None for v in quantity_values) else None
    result = {
        'net_krw': round(total),
        'estimated_value_days':estimate_days,
        'net_qty_shares':net_qty,
        'value_basis':('closing_price_times_net_shares_estimate'
                       if estimate_days else 'reported_net_trading_cash'),
        'buy_days': positive,
        'observed_days': n,
        'buy_day_ratio_pct': round(positive/n*100, 1),
        'positive_streak': streak,
        # Sum of daily close*volume is an APPROXIMATION, not KRX traded value.
        'net_to_value_proxy_pct': round(total/proxy*100, 2) if proxy > 0 else None,
        'begin': dates[0], 'end': dates[-1]
    }
    if n == 20 and len(vals) >= 10:
        result['last_5_net_krw'] = round(sum(vals[-5:]))
        result['prior_5_net_krw'] = round(sum(vals[-10:-5]))
        result['acceleration_krw'] = round(sum(vals[-5:])-sum(vals[-10:-5]))
    return result


def actor_quality(price_rows, flow_rows, actor, price_technical=None):
    windows = {str(n): month_data(price_rows, flow_rows, actor, n)
               for n in WINDOWS}
    recent = windows['5']
    monthly = windows['20']
    if recent is None or monthly is None:
        return {'label': '판정 보류 · 20거래일 미확보',
                'level': 'unknown', 'score': None,
                'windows': windows, 'reasons': ['20거래일 연속 실측 부족']}
    score = 0
    reasons = []
    p20, p5 = monthly['net_krw'] > 0, recent['net_krw'] > 0
    if p20:
        score += 2
        reasons.append('20거래일 누적 순매수')
    else:
        reasons.append('20거래일 누적 순매도')
    if p5:
        score += 2
        reasons.append('5거래일 순매수')
    else:
        reasons.append('5거래일 순매도')
    if monthly['buy_day_ratio_pct'] >= 60:
        score += 1
        reasons.append('최근 20일 중 60% 이상 매수일')
    if monthly['acceleration_krw'] > 0:
        score += 1
        reasons.append('최근 5일 순매수가 직전 5일 대비 개선')
    if (monthly['net_to_value_proxy_pct'] is not None
            and monthly['net_to_value_proxy_pct'] >= 1):
        score += 1
        reasons.append('20일 거래대금 근사 대비 순매수 1% 이상')
    prices = price_rows[-20:]
    pfirst, plast = num(prices[0].get('close_krw')), num(prices[-1].get('close_krw'))
    price_rising = bool(pfirst and plast and plast > pfirst)
    if price_rising:
        score += 1
        reasons.append('20거래일 가격 상승 동행')
    else:
        reasons.append('20거래일 가격 상승 미확인')
    # Optional evidence from latest available KRX market OHLCV indicators.
    if price_technical and price_technical.get('date') == prices[-1]['date']:
        last_close = num(price_technical.get('close'))
        ma20 = num(price_technical.get('ma20'))
        vr = num(price_technical.get('volume_ratio20'))
        if last_close and ma20 and last_close >= ma20:
            score += 1
            reasons.append('20일 이동평균 위')
        if vr and vr >= 1.2 and p5:
            score += 1
            reasons.append('거래량 동반 단기 순매수')
    # A score cannot override a negative 20-session net trend.
    if not p20:
        label, level = ('순매도 우위 · 단기 매수 반전 관찰', 'mixed') if p5 else ('매도 우위 · 수급 약함', 'weak')
    elif not price_rising and p5:
        label, level = '역행 매수 · 주가 확인 대기', 'watch'
    elif score >= 7 and p5:
        label, level = '지속 매집 우위 (기술적 확인 조건)', 'strong'
    elif score >= 5 and p5:
        label, level = '순매수 개선 · 지속성 점검', 'positive'
    elif not p5:
        label, level = '20일 순매수지만 단기 매도 전환', 'mixed'
    else:
        label, level = '순매수 관찰 · 확인 부족', 'watch'
    if monthly.get('estimated_value_days',0):
        reasons.append('비공식 공개 종목 화면의 순매수 주수 기반 · 금액은 종가 환산 추정')
        if level=='strong':
            label, level = '매집 지속성 관찰 (추정 수급)', 'positive'
        elif level=='positive':
            label = label+' (참고 주수)'
    return {'label': label, 'level': level, 'score': score,
            'max_score': 10, 'windows': windows, 'reasons': reasons,
            'price_20d_change_pct': round((plast/pfirst-1)*100, 2) if pfirst and plast else None,
            'note': '점수는 분석 규칙 충족 합계이며 수익률·승률 예측이 아님'}


def evaluate(price_rows, flow_rows, short_rows=None, lending_rows=None,
             technical_rows=None, now=None, _include_asof=True):
    now = now or datetime.now(timezone.utc).isoformat(timespec='seconds')
    prices = sorted([x for x in price_rows if x.get('date')], key=lambda x:x['date'])
    latest_price = prices[-1]['date'] if prices else None
    price_by_day = {r['date']: r for r in (technical_rows or []) if r.get('date')}
    by_date = {r['date']: r for r in flow_rows if r.get('date')}
    valid_flows = [by_date[d] for d in sorted(by_date)
                   if any(num(by_date[d].get(a)) is not None for a in ACTORS)]
    last_flow = valid_flows[-1]['date'] if valid_flows else None
    last_technical = price_by_day.get(latest_price or '', {})
    actor_results = {k: actor_quality(prices, valid_flows, k, last_technical)
                     for k in ACTORS}
    synced = bool(latest_price and latest_price == last_flow)
    foreign = actor_results['foreign']
    inst = actor_results['institution']
    pension = actor_results['pension']
    f5 = foreign['windows']['5']
    i5 = inst['windows']['5']
    f20 = foreign['windows']['20']
    i20 = inst['windows']['20']
    p20 = pension['windows']['20']
    # No invented combined quality when last day, either feed, or 20d is absent.
    if not synced or any(x is None for x in (f20, i20, f5, i5)):
        combined = {'label': '종합 수급 판정 보류', 'level': 'unknown',
                    'detail': '최신 주가와 수급 일자 및 5·20거래일 연속 관측 확인 필요'}
    else:
        combined20 = f20['net_krw'] + i20['net_krw']
        combined5 = f5['net_krw'] + i5['net_krw']
        if combined20 > 0 and combined5 > 0:
            last20_prices=prices[-20:]
            price_confirmed=(bool(last20_prices) and
              (num(last20_prices[-1].get('close_krw')) or 0) >=
              (num(last20_prices[0].get('close_krw')) or float('inf')))
            if (p20 and p20['net_krw'] > 0 and price_confirmed
                and all(x['level'] in ('positive','strong') for x in (foreign, inst))):
                combined = {'label': '외국인·기관 동반 매집 관찰',
                            'level': 'positive',
                            'detail': '5·20거래일 합계 순매수, 연기금 동참; 주가·거래량의 지속 확인 필요'}
            else:
                combined = {'label': '주요 수급 단기 우위 · 연기금 확인 필요',
                            'level': 'watch',
                            'detail': '외국인+기관은 5·20일 순매수이나 연기금·가격 추세 확인 필요'}
        elif combined20 < 0:
            combined = {'label': '20거래일 주요 수급 매도 우위',
                        'level': 'weak',
                        'detail': '외국인+기관 장기 매도 우위. 단기 반등만으로 매집 확정 불가'}
        else:
            combined = {'label': '주요 수급 엇갈림 · 확인 대기',
                        'level': 'mixed',
                        'detail': '5·20일 주요 투자자 순매수 방향이 일치하지 않음'}
        combined['foreign_plus_inst_5d_krw'] = combined5
        combined['foreign_plus_inst_20d_krw'] = combined20
    if any(
        (r.get('amount_estimated') for r in valid_flows[-20:])):
        combined['value_basis']='closing_price_times_net_shares_estimate'
        if combined['level']=='positive':
            combined['level']='watch'
            combined['label']='외국인·기관 동반 매수 지속 (참고·가격 확인 필요)'
        combined['detail']=combined.get('detail','') + (
            ' · 순매수 금액은 Naver 공개 KRX 주수 × 당일 KRX 종가 추정치이며'
            ' 공식 순매수 거래대금 아님. 연기금은 미공개.')
    short = sorted(short_rows or [], key=lambda x:x.get('date') or '')
    lending = sorted(lending_rows or [], key=lambda x:x.get('date') or '')
    short20 = short[-20:]
    ratio = [num(x.get('short_value_ratio_pct')) for x in short20]
    ratio = [x for x in ratio if x is not None]
    # A 20-day SHORT-VOLUME percentage is calculated using the SUM of
    # verified short volume / SUM of total traded volume on exactly the
    # last 20 PRICE sessions; never average daily percentages.
    last20_sessions=prices[-20:] if len(prices)>=20 else []
    short_by_date={r['date']:r for r in short if r.get('date')}
    q_pairs=[]
    if len(last20_sessions)==20:
        for row in last20_sessions:
            sh=short_by_date.get(row['date'],{})
            sq=num(sh.get('short_trade_qty'))
            aq=num(sh.get('total_traded_qty'))
            if sq is None or aq is None or aq<=0:
                q_pairs=[]
                break
            q_pairs.append((sq,aq))
    short_volume_period20=round(
        sum(sq for sq,aq in q_pairs)/sum(aq for sq,aq in q_pairs)*100,2
    ) if len(q_pairs)==20 and sum(aq for _,aq in q_pairs)>0 else None
    lent = lending[-1] if lending else {}
    prior_lent = lending[-2] if len(lending) >= 2 else {}
    # Borrowed shares are NOT the same as a reportable net short balance;
    # repayment could arise for reasons other than covering short sales.
    asof = None
    if _include_asof and not synced:
        common = [p['date'] for p in prices if p['date'] in by_date
                  and any(num(by_date[p['date']].get(a)) is not None for a in ACTORS)]
        if common:
            cutoff = max(common)
            snapshot = evaluate(
                [p for p in prices if p['date'] <= cutoff],
                [r for r in valid_flows if r['date'] <= cutoff],
                technical_rows=technical_rows, now=now, _include_asof=False)
            asof = {'date': cutoff,
                    'lag_price_sessions': sum(p['date'] > cutoff for p in prices),
                    'actors': snapshot['actors'], 'combined': snapshot['combined'],
                    'note': '마지막 공통 거래일까지의 참고 분석. 최신 주가일 판단이 아님'}
    return {
        'asof_analysis': asof,
        'generated_at_utc': now,
        'ticker': '278470',
        'source_scope': '투자자 수급·공매도·대차는 별도 자료이며 각 관측의 source/source_url 및 기준일을 따름',
        'price_last_date': latest_price, 'flow_last_date': last_flow,
        'price_aligned': synced,
        'actors': actor_results, 'combined': combined,
        'latest_daily': valid_flows[-1] if valid_flows else {},
        'short': {
            'last_date': short[-1].get('date') if short else None,
            'latest': short[-1] if short else None,
            'short_ratio_mean20_pct': round(sum(ratio)/len(ratio), 2)
                                      if len(ratio)==20 else None,
            'short_volume_period20_pct':short_volume_period20,
            'ratio_points20': len(ratio),
            'note': '공매도 거래비중과 순보유잔고는 별개; 순보유잔고는 T+2 신고 지연'
        },
        'lending': {
            'last_date': lent.get('date'),
            'latest': lent or None,
            'balance_change': (round(num(lent['balance_qty'])-num(prior_lent['balance_qty']))
                if lent.get('balance_qty') is not None and
                   prior_lent.get('balance_qty') is not None else None),
            'note': '대차잔고 증가 ≠ 공매도 실행. 대차 상환 ≠ 숏커버 확정'
        },
        'methods': {
            'windows': [5,20,60],
            'quality': '20일 실측과 5일 수급 지속성·거래대금 대비 강도·주가 동행으로 분류',
            'normalizer': '일별 종가×거래량 근사 거래대금; 실제 KRX 거래대금 아님',
            'alignment': '마지막 수급일과 마지막 주가일이 일치하지 않으면 종합 판정 보류',
            'double_counting': '연기금은 기관 합계 내 포함; 외국인+기관 계산에 연기금 중복 더하지 않음'
        },
        'not_trade_advice': True
    }


def refresh_saved_analysis(data_dir):
    """Re-evaluate saved observations offline; never claim a new source check."""
    import json
    path = data_dir / 'flows.json'
    if not path.exists():
        return
    current = json.loads(path.read_text(encoding='utf-8'))
    market = json.loads((data_dir / 'market.json').read_text(encoding='utf-8'))
    tech_path = data_dir / 'technical.json'
    technical = json.loads(tech_path.read_text(encoding='utf-8')) if tech_path.exists() else {}
    analysis = evaluate(market.get('series') or [], current.get('daily') or [],
                        current.get('short_daily') or [], current.get('lending_daily') or [],
                        technical.get('series') or [])
    current.update(analysis)
    path.write_text(json.dumps(current, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
