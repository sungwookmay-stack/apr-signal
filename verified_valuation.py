"""Point-in-time basic EPS/BPS from independently read primary filings.
No inference from consolidated total profit, rounded quarterly tables or end shares.
"""
import datetime as dt
import json
from pathlib import Path

SOURCE = Path(__file__).resolve().parent / 'config/apr_verified_valuation.json'


def input_issue(r):
    if r.get('quality_issue'):
        return r['quality_issue']
    end = dt.date.fromisoformat(r['asof'])
    days = r['weight_days']
    if days != (end-dt.date(end.year,1,1)).days+1:
        return '공시 누적 가중치와 달력 기간일수 불일치'
    if days <= 0 or r['share_days_ytd'] <= 0:
        return '주식 적수/기간일수 오류'
    weighted = r['share_days_ytd']/days
    if abs(weighted-r['weighted_average_basic_shares']) > 1:
        return '공시 가중평균 주식수와 적수 대조 불일치'
    reported = r.get('reported_basic_eps_won')
    if reported is not None and abs(r['profit_parent_ytd_won']/weighted-reported) > 1:
        return '원문 기본 EPS와 순이익/가중평균 주식수 대조 불일치'
    return None


def build(manifest=None):
    if manifest is None:
        manifest = json.loads(SOURCE.read_text(encoding='utf-8'))
    reports = sorted(manifest['reports'], key=lambda r: r['asof'])
    by_date = {r['asof']: r for r in reports}
    eps, book, audit = [], [], []
    for r in reports:
        end = dt.date.fromisoformat(r['asof'])
        available = (dt.date.fromisoformat(r['published_on']) + dt.timedelta(days=1)).isoformat()
        common = {k: r[k] for k in ('period', 'asof', 'published_on', 'source_url')}
        common.update(available_from=available, source=r['period']+' 공식 재무제표·주당이익 주석')
        outstanding = r['issued_common_shares'] - r['treasury_common_shares']
        if outstanding <= 0 or r['parent_equity_won'] <= 0:
            raise ValueError('Invalid equity/share denominator: '+r['period'])
        book.append({**common, 'equity_100m': r['parent_equity_won']/1e8,
                     'shares': outstanding, 'bps_won': round(r['parent_equity_won']/outstanding, 2),
                     'issued_shares': r['issued_common_shares'], 'treasury_shares': r['treasury_common_shares'],
                     'equity_basis': 'parent_equity', 'share_basis': 'period_end_ex_treasury'})
        profit, share_days, days = r['profit_parent_ytd_won'], r['share_days_ytd'], r['weight_days']
        issue = input_issue(r)
        components = [r['period']]
        if end.month != 12:
            fy = by_date.get(f'{end.year-1}-12-31')
            prev_date = end.replace(year=end.year-1).isoformat()
            prev = r.get('prior_ytd') or by_date.get(prev_date)
            if not fy or not prev:
                issue = 'TTM 비교기간 원문 미검증'
            else:
                issue = issue or input_issue(fy) or input_issue(prev)
                profit += fy['profit_parent_ytd_won'] - prev['profit_parent_ytd_won']
                share_days += fy['share_days_ytd'] - prev['share_days_ytd']
                days += fy['weight_days'] - prev['weight_days']
                components += [fy['period'], prev_date+' 차감']
        calendar_days = (end - end.replace(year=end.year-1)).days
        if days != calendar_days:
            issue = issue or f'공시 적수 기간 {days}일과 TTM 달력 {calendar_days}일 불일치'
        weighted = share_days / days if days > 0 else None
        eps.append({**common, 'eps_won': round(profit/weighted, 2) if not issue and weighted else None,
                    'shares': weighted, 'ttm_net_income_100m': profit/1e8,
                    'ttm_share_days': share_days, 'ttm_days': days,
                    'component_periods': components, 'eps_quality': 'excluded' if issue else 'primary_verified_basic_ttm',
                    'quality_issue': issue, 'attributable_verified': not bool(issue),
                    'profit_basis': 'parent_attributable', 'share_basis': 'ttm_weighted_average_ex_treasury',
                    'reported_basic_eps_won': r['reported_basic_eps_won'],
                    'reported_diluted_eps_won': r['reported_diluted_eps_won']})
        audit.append({**r, 'available_from': available, 'outstanding_shares': outstanding,
                      'ttm_status': 'excluded' if issue else 'verified', 'quality_issue': issue})
    return {'eps_events': eps, 'book_events': book, 'primary_audit': audit,
            'verified_on': manifest['verified_on'], 'corporate_actions': manifest['corporate_actions'],
            'policies': manifest['policy']}
