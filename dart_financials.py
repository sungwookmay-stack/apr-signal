#!/usr/bin/env python3
"""OpenDART authenticated CFS checks for APR 278470, no extra credentials.

Read official consolidated quarterly/annual XBRL-derived accounts into a
source-preserving JSON. Use only confirmed report entries; never turn a 013
(no filing) into zero. Existing independently reviewed APR PDF numbers are
retained until the new API numbers are validated. The API secret is never
saved, printed or exposed in browser code.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import re
from pathlib import Path
from urllib import parse, request

from dart_ownership import read,save,http_fetch,resolve_corp_code,ENDPOINTS

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'data/dart_financials.json'
OWNERSHIP=ROOT/'data/dart_ownership.json'
BASE='https://opendart.fss.or.kr/api/'
PLANS=(
 ('2025Q1',2025,'11013'),('2025Q2',2025,'11012'),
 ('2025Q3',2025,'11014'),('2025FY',2025,'11011'),
 ('2026Q1',2026,'11013'),('2026Q2',2026,'11012'),
 ('2026Q3',2026,'11014'),('2026FY',2026,'11011'),
)
# Multiple financial statement lines may contain a matching substring.
# Only exact account_id or exact Korean account names are considered.
ACCOUNT_KEYS={
 'sales':('IS','매출액','매출','영업수익'),
 'operating_profit':('IS','영업이익','영업이익(손실)'),
 'net_income':('IS','당기순이익','당기순이익(손실)'),
 'attributable_net_income':('IS','지배기업 소유주지분 순이익','지배기업의 소유주에게 귀속되는 당기순이익'),
 'parent_equity':('BS','지배기업의 소유주에게 귀속되는 자본','지배기업 소유주지분'),
 'cost_of_sales':('IS','매출원가'),
 'sga':('IS','판매비와관리비','판매관리비'),
 'inventory':('BS','재고자산'),
 'assets':('BS','자산총계'),
 'equity':('BS','자본총계'),
 'liabilities':('BS','부채총계'),
 'cash':('BS','현금및현금성자산'),
 'receivables':('BS','매출채권','매출채권 및 기타채권'),
 'cfo':('CF','영업활동현금흐름','영업활동으로 인한 현금흐름'),
}
IFRS_IDS={
 'sales':{'ifrs-full_Revenue','ifrs_Revenue'},
 'operating_profit':{'dart_OperatingIncomeLoss','ifrs-full_ProfitLossFromOperatingActivities'},
 'net_income':{'ifrs-full_ProfitLoss','ifrs_ProfitLoss'},
 'attributable_net_income':{'ifrs-full_ProfitLossAttributableToOwnersOfParent'},
 'parent_equity':{'ifrs-full_EquityAttributableToOwnersOfParent'},
 'cost_of_sales':{'ifrs-full_CostOfSales','ifrs_CostOfSales'},
 'inventory':{'ifrs-full_Inventories','ifrs_Inventories'},
 'assets':{'ifrs-full_Assets','ifrs_Assets'},
 'equity':{'ifrs-full_Equity','ifrs_Equity'},
 'liabilities':{'ifrs-full_Liabilities','ifrs_Liabilities'},
 'cash':{'ifrs-full_CashAndCashEquivalents','ifrs_CashAndCashEquivalents'},
 'receivables':{'ifrs-full_TradeAndOtherCurrentReceivables','ifrs-full_TradeReceivables'},
 'cfo':{'ifrs-full_CashFlowsFromUsedInOperatingActivities'},
}

def amt(value):
    if value in (None,'','-','—'):return None
    try:
        n=int(str(value).replace(',','').replace(' ',''))
        if abs(n)>1_000_000_000_000_000_000:return None
        return n
    except (TypeError,ValueError):
        return None

def simple_name(x):
    return re.sub(r'[\s()\[\]]','',str(x or '').replace('·','').replace('ㆍ',''))

def extract_accounts(items,year,code):
    """Use exact names/IDs and quarter-only amount for IS/CIS, YTD for CF.

    Do not mistake quarter revenue for YTD: DART thstrm_amount represents
    3-month amount for interim income statements. The CF's amount is YTD.
    """
    candidates={key:[] for key in ACCOUNT_KEYS}
    receipts=set()
    for row in items or []:
        if not isinstance(row,dict) or row.get('sj_div') not in ('IS','CIS','BS','CF'):continue
        receipt=str(row.get('rcept_no') or '')
        if re.fullmatch(r'\d{14}',receipt):receipts.add(receipt)
        acc=str(row.get('account_id') or '')
        nm=simple_name(row.get('account_nm'))
        sj=row.get('sj_div')
        for key,(required,*labels) in ACCOUNT_KEYS.items():
            if sj != required and not (required=='IS' and sj=='CIS'):
                continue
            match_id=acc in IFRS_IDS.get(key,set())
            match_name=nm in {simple_name(y) for y in labels}
            if not match_id and not match_name:continue
            raw=amt(row.get('thstrm_amount'))
            cumulative=amt(row.get('thstrm_add_amount'))
            if raw is None:continue
            score=3 if match_id else 2
            if sj==required:score+=1
            candidates[key].append((score,raw,cumulative,acc,nm))
    out={}
    for key,c in candidates.items():
        if not c:continue
        c=sorted(c,reverse=True)
        best=c[0]
        # Prefer unique highest-scored item, reject ambiguous equal-scored
        # conflicting values rather than silently selecting arbitrary values.
        if len(c)>1 and c[1][0]==best[0] and c[1][1]!=best[1]:
            continue
        out[key]={'value_won':best[1],'ytd_won':best[2],
                  'account_id':best[3],'account_name':best[4],
                  'unit':'KRW','amount_basis':(
                      'current_3months' if code!='11011' and key in
                      ('sales','operating_profit','net_income','cost_of_sales','sga')
                      else 'year_to_date_or_balance'
                  )}
    verified_income=all(key in out for key in ('sales','operating_profit','net_income')) and out['sales']['value_won']>=0
    balanced=all(key in out for key in ('assets','equity','inventory'))
    return {'status':'verified_income' if verified_income else
                  'partial_accounts',
            'income_complete':verified_income,
            'balance_complete':balanced,
            'accounts':out,'receipt_numbers':sorted(receipts)}

def parse_api_response(data,year,reprt_code,corp_code):
    if not isinstance(data,dict):return {'status':'invalid_response'}
    stat=str(data.get('status',''))
    if stat=='013':return {'status':'no_disclosure','accounts':{}}
    if stat!='000' or not isinstance(data.get('list'),list):
        return {'status':'api_status_'+re.sub(r'[^0-9]','',stat)[:4], 'accounts':{}}
    rows=[x for x in data['list'] if
          str(x.get('corp_code') or '').zfill(8)==corp_code and
          str(x.get('bsns_year') or '')==str(year) and
          str(x.get('reprt_code') or '')==str(reprt_code) and
          str(x.get('currency') or 'KRW').upper() in ('KRW','원','')]
    if not rows:
        return {'status':'no_matching_cfs','accounts':{}}
    return extract_accounts(rows,year,reprt_code)

def query_full_cfs(transport,key,corp,year,code):
    params={'crtfc_key':key,'corp_code':corp,'bsns_year':year,
            'reprt_code':code,'fs_div':'CFS'}
    url=BASE+'fnlttSinglAcntAll.json?'+parse.urlencode(params)
    try:
        raw=transport(url)
        doc=json.loads(raw.decode('utf-8'))
        return parse_api_response(doc,year,code,corp)
    except Exception as ex:
        return {'status':'connection_error_'+type(ex).__name__,'accounts':{}}

def refresh(key=None,transport=None,output=OUTPUT,now=None):
    key=key if key is not None else os.environ.get('DART_API_KEY','')
    old=read(output,{})
    if not key:
        result={**old,'status':'DART_API_KEY 미확인 · 기존 연결재무 공시 보존',
                'error_type':'MISSING_SECRET'}
        save(output,result);return result
    transport=transport or http_fetch
    now=now or dt.datetime.now(dt.timezone.utc)
    date=now.astimezone(dt.timezone.utc).isoformat(timespec='seconds')
    parent=read(OWNERSHIP,{})
    corp=parent.get('corp_code') or old.get('corp_code')
    if not re.fullmatch(r'\d{8}',str(corp or '')):
        try:
            # Only server-side, and the complete API key never appears in output.
            zipurl=BASE+'corpCode.xml?'+parse.urlencode({'crtfc_key':key})
            corp=resolve_corp_code(transport(zipurl))
        except Exception as exc:
            result={**old,'checked_at_utc':date,
                    'status':'OpenDART 기업 식별 실패 · 종전 재무자료 보존',
                    'error_type':type(exc).__name__}
            save(output,result);return result
    records={x['period']:x for x in old.get('filings',[]) if
             isinstance(x,dict) and x.get('period')}
    attempted=0;success=0
    for period,year,code in PLANS:
        # Do not request future unreleased annual reports.
        if year>now.year:continue
        if year==now.year and code=='11011' and now.month<3:continue
        attempted+=1
        doc=query_full_cfs(transport,key,corp,year,code)
        # Preserve a previously verified report on transient no-data/403.
        if doc.get('status') in ('verified_income','partial_accounts'):
            if doc.get('accounts'):
                records[period]={
                    'period':period,'bsns_year':year,'reprt_code':code,
                    'fs_div':'CFS','checked_at_utc':date,
                    **doc
                }
                success+=1
    reports=sorted(records.values(),key=lambda x:x['period'])
    result={
        'company':'에이피알','stock_code':'278470','corp_code':corp,
        'checked_at_utc':date,
        'last_successful_check_utc':date if success else old.get('last_successful_check_utc'),
        'status':'OpenDART 연결재무제표 확인' if success else '신규 확인 실패 · 기존 공식 수치 보존',
        'report_count':len(reports),'verified_during_run':success,
        'requests_attempted':attempted,
        'filings':reports,'data_scope':'공식 연결재무제표 CFS 계정별 원본. 감사 PDF와 차이·재작성 여부를 대조 후 대시보드에 반영.',
        'notes':[
           '3개월 손익은 thstrm_amount, 현금흐름은 당기누적; FY-3Q로 분리 계산할 수 있으나 이중차감 금지.',
           '연결·별도 및 계정명 중복이 있을 때 자동으로 억지 매핑하지 않음.',
           '정기보고서 미제출은 실적 0원이 아니라 미공개를 의미.',
           'DART 인증키는 서버 환경변수에만 저장하고 공개 JSON/로그에 기록하지 않음.'
        ],
    }
    save(output,result)
    print(json.dumps({'status':result['status'],'reports':result['report_count'],
                      'confirmed_this_run':success,'requests':attempted},ensure_ascii=False))
    return result

if __name__=='__main__':
    refresh()
