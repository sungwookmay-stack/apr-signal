#!/usr/bin/env python3
"""APR SIGNAL financial ratios and as-of-date valuation anchors.

Inputs are reviewed, dated IFRS filings in config/apr_financial_source.json.
Never mix preliminary quarter numbers with unpublished balance sheet fields.
PER/PBR bands are built on the client from actual daily prices and dated
EPS/BPS release events, avoiding look-ahead.
"""
from __future__ import annotations
import datetime as dt
import json
from valuation_audit import reconcile
from verified_valuation import build as verified_valuation
from pathlib import Path

ROOT = Path(__file__).resolve().parent
INPUT = ROOT/'config/apr_financial_source.json'
OUTPUT = ROOT/'data/financials.json'


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def ratio(n,d):
    if n is None or d is None or d == 0: return None
    return round(100*n/d, 2)


def rounded(n,d=2):
    return None if n is None else round(n,d)


def growth_comparison(current, original, explicit=None):
    """Never divide IFRS18 earnings by a pre-IFRS18 comparative.

    A reviewed comparative is separate from the historical original row.
    Missing or mismatched bases are not silently assumed comparable.
    """
    candidate = explicit if explicit is not None else original
    if not candidate:
        return None, '비교기간 없음'
    if explicit is not None and (not original or candidate.get('period') != original.get('period')
                                 or not candidate.get('source_url')):
        return None, '검증된 비교기간·원문 없음'
    basis = current.get('income_accounting_basis')
    if not basis or candidate.get('income_accounting_basis') != basis:
        return None, '회계기준 불일치 또는 미확인'
    return candidate, ('공식 IR 동일기준 재작성 비교' if explicit is not None else '동일기준 원공시 비교')


def reviewed_q3(dart):
    # Only use the reviewed official CFS receipt and explicit amount bases.
    receipts = [q for q in (dart or {}).get('filings',[]) if
        q.get('period')=='2026Q3' and q.get('fs_div')=='CFS' and
        q.get('income_complete') and q.get('balance_complete') and
        q.get('receipt_numbers')==['20261113001366']]
    if len(receipts)!=1:return {}, {}
    accounts=receipts[0].get('accounts',{})
    def amount(name, basis):
        r=accounts.get(name,{})
        v=r.get('value_won')
        if r.get('unit')!='KRW' or r.get('amount_basis')!=basis or type(v)!=int or v<0:
            raise ValueError(name)
        return v
    try:
        income={k:amount(a,'current_3months') for k,a in (
            ('sales','sales'),('op','operating_profit'),('ni','net_income'),
            ('cogs','cost_of_sales'),('sga','sga'))}
        balance={k:amount(k,'year_to_date_or_balance') for k in
            ('inventory','assets','equity','liabilities','cash','receivables')}
        if income['sales']<income['cogs'] or income['sga']>income['sales'] or balance['assets']!=balance['equity']+balance['liabilities']:
            return {}, {}
    except ValueError:
        return {}, {}
    income['gross']=income['sales']-income['cogs']
    source_url='https://dart.fss.or.kr/dsaf001/main.do?rcpNo=20261113001366'
    source={'source':'OpenDART 2026Q3 분기보고서 연결재무제표','source_url':source_url,'available_from':'2026-11-13'}
    return ({**{k:round(v/1e8,2) for k,v in income.items()}, **source,
             'status':'정기보고서 연결 확정 공시'},
            {**{k:round(v/1e8,2) for k,v in balance.items()}, **source,
             'period':'2026Q3','asof':'2026-09-30','reported_inventory_turnover':None,'shares':None})


def reviewed_q3_cost_cash(details, confirmed):
    # Time-gate reviewed notes to the same validated statutory filing as income.
    if (not confirmed or details.get('available_from') != confirmed.get('available_from')
            or details.get('receipt_number') != '20261113001366'
            or not confirmed.get('source_url', '').endswith(details['receipt_number'])):
        return {}
    out = {}
    costs = details.get('sga_detail_audit', {})
    fields = ('ads', 'logistics', 'fees')
    if (costs.get('basis') == 'consolidated_Note_20_current_3months'
            and costs.get('unit') == 'KRW_thousand'
            and all(type(costs.get(k)) is int and costs[k] >= 0 for k in fields)
            and sum(costs[k] for k in fields) / 1e5 <= confirmed['sga']):
        out.update({k: round(costs[k] / 1e5, 2) for k in fields})
        out['sga_detail_audit'] = {**costs, 'source_url': confirmed['source_url']}
    cash = details.get('cash_flow_audit', {})
    fields = ('cfo_ytd_won', 'prior_cfo_ytd_won', 'tangible_capex_ytd_won',
              'prior_tangible_capex_ytd_won')
    if (cash.get('basis') == 'original_filing_CFS_YTD_differenced'
            and cash.get('source_url') == confirmed['source_url']
            and cash.get('prior_source_url', '').endswith('20260814002503')
            and all(type(cash.get(k)) is int for k in fields)
            and cash['tangible_capex_ytd_won'] >= cash['prior_tangible_capex_ytd_won'] >= 0):
        out.update(cfo=round((cash[fields[0]] - cash[fields[1]]) / 1e8, 2),
                   capex=round((cash[fields[2]] - cash[fields[3]]) / 1e8, 2),
                   cash_flow_audit=cash)
    return out


def build(data, dart=None):
    q3, q3_balance = reviewed_q3(dart)
    quarters=[]
    prior={}
    q3_details={}
    for q in sorted(data['quarterly'],key=lambda x:x['period']):
        x=dict(q)
        details=x.pop('reviewed_filing_details', {})
        if q['period']=='2026Q3' and q3:
            q3_details=reviewed_q3_cost_cash(details, q3)
            q={**x, **q3, **q3_details}
            x=dict(q)
        for name,field in [('gross_margin_pct','gross'),('op_margin_pct','op'),
                           ('net_margin_pct','ni'),('sga_ratio_pct','sga'),
                           ('ads_ratio_pct','ads'),('selling_fee_ratio_pct','fees'),
                           ('shipping_ratio_pct','logistics')]:
            x[name]=ratio(q.get(field),q.get('sales'))
        x['cash_conversion_pct']=ratio(q.get('cfo'),q.get('ni'))
        x['fcf_proxy']=rounded(q['cfo']-q['capex']) if q.get('cfo') is not None and q.get('capex') is not None else None
        prev=prior.get('previous')
        lastyear=next((v for v in quarters if v['period']==str(int(q['period'][:4])-1)+q['period'][4:]),None)
        yoy, yoy_note = growth_comparison(q, lastyear, q.get('yoy_comparative'))
        qoq, qoq_note = growth_comparison(q, prev, q.get('qoq_comparative'))
        x['growth_comparison'] = {
            'yoy': {'status': yoy_note, 'period': yoy.get('period') if yoy else None,
                    'source_url': yoy.get('source_url') if yoy else None},
            'qoq': {'status': qoq_note, 'period': qoq.get('period') if qoq else None},
        }
        for key in ('sales','op','ni'):
            x[key+'_qoq_pct']=rounded((q[key]/qoq[key]-1)*100) if qoq and q.get(key) is not None and qoq.get(key) else None
            x[key+'_yoy_pct']=rounded((q[key]/yoy[key]-1)*100) if yoy and q.get(key) is not None and yoy.get(key) else None
        prior['previous']=q
        quarters.append(x)

    balances=[]
    balance_source=list(data['balance'])
    if q3_balance and not any(b['period']=='2026Q3' for b in balance_source):
        balance_source.append(q3_balance)
    for b in sorted(balance_source,key=lambda x:x['asof']):
        row=dict(b)
        row['inventory_assets_pct']=ratio(b['inventory'],b['assets'])
        row['inventory_days_company']=rounded(365/b['reported_inventory_turnover']) if b.get('reported_inventory_turnover') else None
        row['liabilities_assets_pct']=ratio(b['liabilities'],b['assets'])
        row['inventory_to_receivables']=rounded(b['inventory']/b['receivables']) if b.get('receivables') else None
        balances.append(row)

    # ROE = trailing 12-month consolidated NI / average owners' equity.
    # Only matching start/end balance dates permit a verified calculation.
    balance_by_date={v['asof']:v for v in balances}
    roe_points=[]
    for b in balances:
        end=dt.date.fromisoformat(b['asof'])
        previous_day=dt.date(end.year-1,end.month,end.day)
        base=balance_by_date.get(previous_day.isoformat())
        if base and b.get('equity') and base.get('equity'):
            annual=next((x for x in data.get('annual',[]) if x['asof']==b['asof']),None)
            if annual and annual.get('net_income') is not None:
                ttm=annual['net_income']
            elif b['period']=='2026Q2':
                fy=next(x for x in data['annual'] if x['period']=='2025FY')
                h1=sum(x['ni'] for x in quarters if x['period'] in ('2026Q1','2026Q2'))
                prior_h1=sum(x['ni'] for x in quarters if x['period'] in ('2025Q1','2025Q2'))
                ttm=fy['net_income']-prior_h1+h1
            else:
                ttm=None
            if ttm is not None:
                roe_points.append({
                    'asof':b['asof'],'period':b['period'],
                    'roe_ttm_pct':ratio(ttm,(b['equity']+base['equity'])/2),
                    'ttm_net_income_100m':rounded(ttm),
                    'base_equity_100m':base['equity'],'end_equity_100m':b['equity'],
                    'method':'최근 12개월 연결 순이익 / 전년 동기와 현재 연결 자본총계의 평균; 총자본 ROE 참고치 (지배주주 ROE와 다름)'
                })

    verified = verified_valuation()
    if 'cash_flow_audit' in q3_details and 'sga_detail_audit' in q3_details:
        quality_notice = ('2026Q3은 11월 13일 정기보고서의 연결 실적. 판관비 세부 항목은 주석 20, '
                          '분기 현금흐름은 9개월 누계에서 반기 누계를 차감. 미검증 ROE·ROIC는 미산출.')
    elif q3:
        quality_notice = '2026Q3은 정기보고서 연결 실적. 원문 대조가 완료된 항목만 표시하며 미검증 ROE·ROIC는 미산출.'
    else:
        quality_notice = ('2026Q3은 연결잠정실적. 정기보고서의 재고·광고·판관비·현금흐름·ROE·ROIC는 이 상태에서 미산출. '
                          '이자부채 분류가 완성되기 전 ROIC는 미산출.')
    return {
        'schema_version':2,'generated_at_utc':dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds'),
        'company':data['company'],'ticker':data['ticker'],'unit':data['unit'],
        'quarterly':quarters,'balance':balances,'roe_ttm':roe_points,
        'annual':data.get('annual',[]),
        'valuation':{
            'period_start':'2025-06-01',
            **verified,
            'per_multiples':[15,25,35,45,55],
            'pbr_multiples':[5,10,15,20,25],
            'method_note':'공식 원문 지배주주 기본 TTM EPS 및 자기주식 제외 기말 BPS 기준. EPS 기간일수 불일치 구간은 산출하지 않음.',
            'forward_or_consensus_used':False,
            'share_adjustments_note':'2024년 5:1 분할 소급반영 수치를 사용하며 중복 조정하지 않음. 기본 EPS는 기간 가중평균 유통주식수, BPS는 기말 발행주식수에서 자기주식을 제외. TTM 희석 EPS는 미산출.',
            'multiple_basis':'사용자가 비교하는 고정 배수 시나리오. 역사적 평균·분위수·목표주가 아님.',
        },
        'definitions':data['evaluation'],
        'source_files':data['source_files'],
        'accounting_note':data['accounting_note'].replace('2026Q3은 정식 보고서 이전 잠정실적. ', '') if q3 else data['accounting_note'],
        'dart_reconciliation':reconcile(data, dart or {}),
        'quality_notice':quality_notice,
    }


def update(path=OUTPUT, source=INPUT):
    dart_path=ROOT/'data/dart_financials.json'
    dart=read_json(dart_path) if dart_path.exists() else {}
    result=build(read_json(source), dart)
    Path(path).parent.mkdir(parents=True,exist_ok=True)
    Path(path).write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result


if __name__=='__main__':
    out=update()
    print(json.dumps({'status':'ok','periods':len(out['quarterly']),
                      'latest':out['quarterly'][-1]['period'],
                      'eps_anchors':len(out['valuation']['eps_events']),
                      'book_anchors':len(out['valuation']['book_events'])},ensure_ascii=False))
