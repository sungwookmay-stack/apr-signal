#!/usr/bin/env python3
"""Free OpenDART APR (278470) major/insider ownership filing tracker.

Only the GitHub Actions runner sees DART_API_KEY. Never include it in logs,
saved JSON, HTTP exceptions, or public source URLs. Stock code is NOT corp_code:
resolve the latter from DART's corpCode.xml ZIP using official stock code.

Raw reported 'holding' snapshots are per reporter, NOT additive and NOT an
exchange transaction ledger. Distinguish majorstock (5% etc) from elestock
(executive and major-shareholder securities reports).
"""
from __future__ import annotations
import datetime as dt
import io
import json
import os
from pathlib import Path
import re
from urllib import parse, request
from xml.etree import ElementTree as ET
from zipfile import ZipFile

ROOT=Path(__file__).resolve().parent
OUTPUT=ROOT/'data/dart_ownership.json'
API='https://opendart.fss.or.kr/api/'
SOURCE='https://dart.fss.or.kr/dsaf001/main.do?rcpNo='
CODE='278470'
ENDPOINTS={'majorstock':'대량보유(5% 등) 보고','elestock':'임원·주요주주 소유 보고'}

def read(path,default):
    try:return json.loads(Path(path).read_text(encoding='utf-8'))
    except (OSError,ValueError):return default

def save(path,obj):
    target=Path(path);target.parent.mkdir(parents=True,exist_ok=True)
    target.write_text(json.dumps(obj,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')

def as_number(value,decimal=False):
    raw=str(value if value is not None else '').replace(',','').replace('%','').strip()
    if raw in ('','-','—','N/A','null'):return None
    try:
        n=float(raw) if decimal else int(raw)
        return round(n,4) if decimal else n
    except ValueError:return None

def resolve_corp_code(zip_bytes):
    with ZipFile(io.BytesIO(zip_bytes)) as archive:
        if not archive.namelist():raise ValueError('Missing OpenDART company directory')
        xml=archive.read(archive.namelist()[0])
    for company in ET.fromstring(xml).iter('list'):
        if (company.findtext('stock_code') or '').strip()==CODE:
            name=(company.findtext('corp_name') or '').strip()
            code=(company.findtext('corp_code') or '').strip()
            if len(code)==8 and name.replace('㈜','').strip() in ('에이피알','주식회사 에이피알','(주)에이피알'):
                return code
    raise ValueError('APR 278470 matching OpenDART corp_code not found')

def fetch_json(transport,key,endpoint,corp_code):
    url=API+endpoint+'.json?'+parse.urlencode({'crtfc_key':key,'corp_code':corp_code})
    try:return json.loads(transport(url).decode('utf-8'))
    except Exception as exc:raise RuntimeError('OpenDART '+endpoint+' connection failed: '+type(exc).__name__) from None

def http_fetch(url):
    req=request.Request(url,headers={'User-Agent':'APR stock tracker (independent public disclosure research)',
                                     'Accept':'application/json,application/zip,application/octet-stream'})
    with request.urlopen(req,timeout=17) as resp:return resp.read(7_000_000)

def normalize(endpoint,records,corp_code):
    out=[]
    for raw in records:
        if not isinstance(raw,dict) or str(raw.get('corp_code','')).zfill(8)!=corp_code:continue
        receipt=str(raw.get('rcept_no','')).strip()
        reported=str(raw.get('rcept_dt','')).replace('-','').strip()
        if not re.fullmatch(r'\d{14}',receipt) or not re.fullmatch(r'20\d{6}',reported):continue
        reporter=str(raw.get('repror','')).strip()
        if not reporter:continue
        if endpoint=='majorstock':
            shares=as_number(raw.get('stkqy'))
            delta=as_number(raw.get('stkqy_irds'))
            pct=as_number(raw.get('stkrt'),True)
            pct_delta=as_number(raw.get('stkrt_irds'),True)
            reason=str(raw.get('report_resn') or '')
            subtype=str(raw.get('report_tp') or '')
        else:
            shares=as_number(raw.get('sp_stock_lmp_cnt'))
            delta=as_number(raw.get('sp_stock_lmp_irds_cnt'))
            pct=as_number(raw.get('sp_stock_lmp_rate'),True)
            pct_delta=as_number(raw.get('sp_stock_lmp_irds_rate'),True)
            reason=str(raw.get('isu_exctv_ofcps') or '')
            subtype=str(raw.get('isu_main_shrholdr') or raw.get('isu_exctv_rgist_at') or '')
        out.append({
            'type':endpoint,'type_label':ENDPOINTS[endpoint],
            'date':f'{reported[:4]}-{reported[4:6]}-{reported[6:]}',
            'reporter':reporter[:100],'receipt_no':receipt,
            'shares_reported':shares,'shares_change_reported':delta,
            'ownership_pct':pct,'ownership_pct_change':pct_delta,
            'reason':reason[:180],'report_type':subtype[:100],
            'source_url':SOURCE+receipt,
            'provenance':'OpenDART public ownership disclosure; reporter-level observation'
        })
    return out

def refresh(key=None,transport=None,output=OUTPUT,now=None):
    key=key if key is not None else os.environ.get('DART_API_KEY','')
    previous=read(output,{})
    if not key:
        result={**previous,'status':'DART_API_KEY 환경변수 미등록 · 확인된 기존 공시는 유지',
                'ready':False,'error_type':'MISSING_SECRET'}
        save(output,result);return result
    transport=transport or http_fetch
    now=now or dt.datetime.now(dt.timezone.utc)
    checked=now.astimezone(dt.timezone.utc).isoformat(timespec='seconds')
    corp=previous.get('corp_code')
    if not corp or not re.fullmatch(r'\d{8}',str(corp)):
        url=API+'corpCode.xml?'+parse.urlencode({'crtfc_key':key})
        try:corp=resolve_corp_code(transport(url))
        except Exception as exc:
            result={**previous,'checked_at_utc':checked,'ready':False,
                    'status':'OpenDART 기업 고유번호 확인 실패; 기존 기록 유지',
                    'error_type':type(exc).__name__}
            save(output,result);return result
    old=[x for x in previous.get('filings',[]) if x.get('type') in ENDPOINTS
         and re.fullmatch(r'\d{14}',str(x.get('receipt_no','')))]
    keyed={(x['type'],x['receipt_no'],x['reporter']):x for x in old}
    statuses={};success=0
    for endpoint in ENDPOINTS:
        try:
            obj=fetch_json(transport,key,endpoint,corp)
            status=str(obj.get('status',''))
            if status=='013':
                statuses[endpoint]='공시 조회 0건 (신규 자료 없음)'
                success+=1
                continue
            if status!='000' or not isinstance(obj.get('list'),list):
                statuses[endpoint]='공식 API 조회 불완전 · 코드 '+re.sub(r'[^0-9A-Z]','',status)[:8]
                continue
            for x in normalize(endpoint,obj['list'],corp):
                keyed[(endpoint,x['receipt_no'],x['reporter'])]=x
            statuses[endpoint]='정상 조회'
            success+=1
        except Exception:
            statuses[endpoint]='연결 실패 · 기존 공시 유지'
    records=sorted(keyed.values(),key=lambda x:(x['date'],x['receipt_no'],x['type']),reverse=True)[:1600]
    previous_success=previous.get('last_successful_check_utc')
    result={
        'company':'에이피알','stock_code':CODE,'corp_code':corp,'unit':'shares; %',
        'checked_at_utc':checked,
        'last_successful_check_utc':checked if success==len(ENDPOINTS) else previous_success,
        'status':'정상 조회' if success==len(ENDPOINTS) else '일부/전체 조회 실패 · 기존 공시 유지',
        'ready':success>0,
        'endpoint_status':statuses,
        'filings':records,'count':len(records),
        'new_disclosures':len(set(keyed)-{(x['type'],x['receipt_no'],x['reporter']) for x in old}),
        'notes':[
          '대량보유 보고와 임원·주요주주 소유보고는 보고 대상·기준이 달라 서로 합산하면 안 됩니다.',
          '공시상 보유주식 및 지분율은 보고자별 시점 자료이며, 증감이 모두 장내 매수·매도라는 의미가 아닙니다.',
          '공시 접수일과 실제 지분변동 발생일이 다를 수 있습니다. 원문 보고사유를 확인해야 합니다.'
        ]
    }
    save(output,result)
    print(json.dumps({'status':result['status'],'filings':len(records),
                      'new_disclosures':result['new_disclosures'],
                      'endpoint_status':statuses},ensure_ascii=False))
    return result

if __name__=='__main__':
    refresh()
