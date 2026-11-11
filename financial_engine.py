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


def build(data, dart=None):
    quarters=[]
    prior={}
    for q in sorted(data['quarterly'],key=lambda x:x['period']):
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
        for key in ('sales','op','ni'):
            x[key+'_qoq_pct']=rounded((q[key]/prev[key]-1)*100) if prev and q.get(key) is not None and prev.get(key) else None
            x[key+'_yoy_pct']=rounded((q[key]/lastyear[key]-1)*100) if lastyear and q.get(key) is not None and lastyear.get(key) else None
        prior['previous']=q
        quarters.append(x)

    balances=[]
    for b in sorted(data['balance'],key=lambda x:x['asof']):
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
            'forward':{'method':'user_scenario','consensus':False,'horizon':'입력한 향후 12개월 또는 회계연도','default_growth_pct':0}
        },
        'definitions':data['evaluation'],
        'source_files':data['source_files'],
        'accounting_note':data['accounting_note'],
        'dart_reconciliation':reconcile(data, dart or {}),
        'quality_notice':'2026Q3은 연결잠정실적. 2026Q3 재고·광고·판관비·ROE·ROIC를 추정하지 않음. 이자부채 분류가 완성되기 전 ROIC는 미산출.',
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
