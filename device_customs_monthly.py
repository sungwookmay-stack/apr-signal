"""Free official monthly HS10 industry reference; never APR-specific exports."""
import datetime as dt
import re
import time
from xml.etree import ElementTree as ET
from customs_monthly import DataError, amount, fetch, month, country_specs, SOURCES

HS = '8543702020'
START = '202506'

def parse_device(body, country, start, end):
    root = ET.fromstring(body)
    rc = root.findtext('.//resultCode') or root.findtext('.//returnReasonCode') or ''
    if rc not in ('00', '0', '000', '0000'):
        raise DataError('api_' + rc if re.fullmatch(r'[A-Za-z0-9]{1,10}', rc) else 'api_error')
    out = {}; total = None
    for item in root.findall('.//item'):
        r = {c.tag:(c.text or '').strip() for c in item}
        if r.get('year') in ('총계', '합계'):
            if total is not None: raise DataError('duplicate_total')
            total = amount(r.get('expDlr')); continue
        m = month(r.get('year'))
        if not start <= m.replace('-', '') <= end: raise DataError('out_of_window')
        if r.get('hsCd') != HS or r.get('statCd') != country: raise DataError('scope_mismatch')
        if m in out: raise DataError('duplicate_month')
        out[m] = amount(r.get('expDlr'))
    if total is not None and total != sum(out.values()): raise DataError('total_mismatch')
    return out

def windows(end, observations):
    # First load/backfill missing months; refresh latest three months for revisions.
    y, m = int(end[:4]), int(end[4:])
    dates=[]
    for year in range(2025,y+1):
        for mo in range(1,13):
            s=f'{year}{mo:02}'
            if START <= s <= end: dates.append(s)
    refresh=set(dates[-3:])
    wanted=[s for s in dates if s[:4]+'-'+s[4:] not in observations or s in refresh]
    # API maximum 1 year, avoid re-fetching full history on every routine run.
    result=[]
    for year in sorted({s[:4] for s in wanted}):
        group=[s for s in wanted if s[:4]==year]
        result.append((min(group),max(group)))
    return result

def collect_device_series(config, prior, key, now, end, retry_only=False):
    old={s['id']:s for s in prior}
    result=[]
    for _, country, _, label in country_specs(config):
        ident=country+'_'+HS
        before=old.get(ident,{})
        obs={o['month']:o for o in before.get('observations',[]) if o['month']>='2025-06'}
        failed=[tuple(e['window']) for e in before.get('errors',[]) if 'window' in e]
        if retry_only and before and not failed:
            result.append(before); continue
        errors=[]; verified=list(before.get('verified_windows',[])) if retry_only else []
        requested=failed if retry_only and before else windows(end,obs)
        for start,stop in requested:
            if not key:
                errors.append({'window':[start,stop],'code':'missing_secret'}); continue
            try:
                raw=fetch('country',key,{'strtYymm':start,'endYymm':stop,'hsSgn':HS,'cntyCd':country})
                records=parse_device(raw,country,start,stop)
                for m,value in records.items():obs[m]={'month':m,'value':value,'verified_at':now.isoformat()}
                verified.append([start,stop])
            except DataError as exc:errors.append({'window':[start,stop],'code':str(exc)})
            except Exception:errors.append({'window':[start,stop],'code':'invalid_response'})
            time.sleep(.25)
        status='missing_secret' if not key else 'partial' if errors and obs else 'api_error' if errors else 'success' if obs else 'no_data'
        result.append({'id':ident,'label':label.split(' · ')[0]+' · 가정형 미용기기',
          'kind':'country','product_category':'beauty_device_industry','hs_code':HS,
          'geography':country,'geography_basis':'한국 수출 목적국','unit':'USD','unit_verified':True,
          'unit_note':'FOB 신고미화금액 달러','source_url':SOURCES['country'],
          'classification_source_url':'https://www.data.go.kr/data/15130660/fileData.do',
          'scope_note':'전국 가정형 미용기기의 목적국별 산업 참고 통계. APR 자체 수출이 아니며 개별 제품의 신고코드는 미확인. 국가별 값을 전국 총계로 합산하지 않음.',
          'status':status,'latest_month':max(obs) if obs else None,
          'observations':[obs[m] for m in sorted(obs)],'checked_at':now.isoformat(),
          'errors':errors,'verified_windows':verified})
    return result
