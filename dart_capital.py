#!/usr/bin/env python3
"""Free APR OpenDART capital return: dividends and treasury-share balances.

Structured observations from submitted periodic reports, not trade tickets
or inferred actual cash returns. Never add rows from different report dates.
Keep old verified observations on failed/currently unpublished documents.
Never store or print DART_API_KEY or secret-bearing URLs.
"""
from __future__ import annotations
import datetime as dt
import json, os, re
from pathlib import Path
from urllib import parse

from dart_ownership import http_fetch, resolve_corp_code, read, save
from dart_financials import PLANS

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'data/dart_capital.json'
API='https://opendart.fss.or.kr/api/'
LINK='https://dart.fss.or.kr/dsaf001/main.do?rcpNo='
FIELDS={
    'alotMatter':'배당에 관한 사항',
    'tesstkAcqsDspsSttus':'자기주식 취득·처분 현황',
}
MAX_PER_RUN=16

def number(v):
    s=str(v or '').strip().replace(',','')
    if s in ('','-','—','해당사항없음','N/A'):return None
    try:
        n=float(s)
        if n < -1e12 or n > 1e12:return None
        return n if '.' in s else int(n)
    except ValueError:return None

def report_url(receipt):
    s=str(receipt or '')
    return LINK+s if re.fullmatch(r'\d{14}',s) else None

def normalize(endpoint,items,corp,period):
    out=[]
    for x in items or []:
        if str(x.get('corp_code') or '').zfill(8)!=str(corp):continue
        receipt=report_url(x.get('rcept_no'))
        if not receipt:continue
        day=str(x.get('stlm_dt') or '').strip()
        if not re.fullmatch(r'20\d\d[-.]?\d\d[-.]?\d\d',day):
            day=None
        if endpoint=='alotMatter':
            field=str(x.get('se') or '').strip()
            if not field:continue
            value=number(x.get('thstrm'))
            if value is None:continue
            # This is a labeled statement fact, NOT automatically the dividend
            # declared or paid for a certain date. Retain the original label.
            out.append({
              'period':period,'asof':day,'type':'dividend',
              'metric':field[:140],'stock_type':str(x.get('stock_knd') or '')[:60],
              'value':value,'raw_value':str(x.get('thstrm'))[:40],
              'source_url':receipt,'receipt_no':x.get('rcept_no'),
              'note':'정기보고서의 당기 배당 관련 계정. 배당 결의/배당지급 여부와 다름'
            })
        elif endpoint=='tesstkAcqsDspsSttus':
            # Keep only explicit total-method rows, not the many breakdowns
            # which would otherwise double count treasury shares.
            c1=str(x.get('acqs_mth1') or '').replace(' ','')
            c2=str(x.get('acqs_mth2') or '').replace(' ','')
            c3=str(x.get('acqs_mth3') or '').replace(' ','')
            if c1!='총계' and c2!='총계' and c3!='총계':continue
            stock=str(x.get('stock_knd') or '').strip()
            if stock and '보통' not in stock:continue
            end=number(x.get('trmend_qy'))
            if end is None:continue
            out.append({
              'period':period,'asof':day,'type':'treasury_total',
              'metric':'공시상 자기주식 기말 보유(총계행)',
              'stock_type':stock,'value':end,'unit':'주',
              'shares_acquired_in_report':number(x.get('change_qy_acqs')),
              'shares_disposed_in_report':number(x.get('change_qy_dsps')),
              'shares_canceled_in_report':number(x.get('change_qy_incnr')),
              'method':(c1+' / '+c2+' / '+c3)[:90],
              'source_url':receipt,'receipt_no':x.get('rcept_no'),
              'note':'정기보고서 총계행 기말 수량. 분기별 매수금액이나 거래 확정 수량으로 해석 불가'
            })
    return out

def refresh(key=None, transport=None, output=OUTPUT, now=None):
    key = key if key is not None else os.environ.get('DART_API_KEY','')
    previous=read(output,{})
    if not key:
        result={**previous,'status':'OpenDART API 키 미연결 / 기존 기록 유지',
                'checked_at_utc':None}
        save(output,result)
        return result
    transport=transport or http_fetch
    now=now or dt.datetime.now(dt.timezone.utc)
    stamp=now.astimezone(dt.timezone.utc).isoformat(timespec='seconds')
    corp=read(ROOT/'data/dart_ownership.json',{}).get('corp_code') or previous.get('corp_code')
    if not re.fullmatch(r'\d{8}',str(corp or '')):
        try:
            corp=resolve_corp_code(transport(API+'corpCode.xml?'+parse.urlencode({'crtfc_key':key})))
        except Exception as exc:
            result={**previous,'status':'OpenDART 기업코드 확인 실패 · 기존 기록 유지',
                    'error_type':type(exc).__name__,'checked_at_utc':stamp}
            save(output,result);return result
    old=[x for x in previous.get('observations',[]) if isinstance(x,dict)]
    new={(x.get('period'),x.get('type'),x.get('metric'),x.get('stock_type'),x.get('method')):x for x in old}
    scanned=0;verified=0;failures=0
    for period,year,code in PLANS:
        if year>now.year or (year==now.year and code=='11011' and now.month<3):continue
        for endpoint in FIELDS:
            scanned+=1
            try:
                url=API+endpoint+'.json?'+parse.urlencode({
                     'crtfc_key':key,'corp_code':corp,
                     'bsns_year':year,'reprt_code':code})
                obj=json.loads(transport(url).decode('utf-8'))
                status=str(obj.get('status') or '')
                if status=='013':continue
                if status!='000' or not isinstance(obj.get('list'),list):
                    failures+=1;continue
                for row in normalize(endpoint,obj['list'],corp,period):
                    keyrow=(row.get('period'),row.get('type'),
                            row.get('metric'),row.get('stock_type'),row.get('method'))
                    new[keyrow]=row
                verified+=1
            except Exception:
                failures+=1
    records=sorted(new.values(),key=lambda r:(r.get('period',''),r.get('metric','')))[-750:]
    result={
        'company':'에이피알','stock_code':'278470','corp_code':corp,
        'checked_at_utc':stamp,
        'last_successful_check_utc':stamp if verified else previous.get('last_successful_check_utc'),
        'status':'공식 정기보고서 일부 또는 전체 확인' if verified else '공식 자료 갱신 미확인 · 기존 기록 유지',
        'observations':records,'observed_count':len(records),
        'report_queries':scanned,'verified_responses':verified,'failed_queries':failures,
        'notes':[
          '주식 수와 배당 항목은 서로 다른 공시 지표입니다. 회사가 실제 지급한 배당액·매입대금을 임의 산출하지 않습니다.',
          '기간별 배당항목은 누계·전년도 비교가 포함될 수 있습니다. 주당 현금배당금과 총 현금배당액을 혼동하지 않습니다.',
          '자기주식 수량은 정기보고서 총계행만 사용하여 세부 취득방법 중복 합산을 방지합니다.'
        ]
    }
    save(output,result)
    print(json.dumps({'dart_capital_status':result['status'],
                      'observations':len(records),'requests':scanned,
                      'verified':verified,'failures':failures},ensure_ascii=False))
    return result

if __name__=='__main__':
    refresh()
