#!/usr/bin/env python3
"""APR daily investor/short/lending collector with source provenance.

Primary daily investor and short sources: KRX Data Marketplace, accessed
through the free pykrx client when installed. This is NOT the KRX Open API
(which currently does not offer investor-by-security/short-sale endpoints).
KSD SLB: optional key in GitHub Actions secret KSD_SLB_API_KEY for
apis.data.go.kr/B552481/SlbSvc/getSlbDealingByIsin.
No API key ever goes into JSON, logs, or client JavaScript.

Missing/blocked endpoints never create zero values or a 'strong-buy' label.
No public third-party daily investor summaries are silently reclassified as
the official KRX time series.
"""
from __future__ import annotations
import csv
import datetime as dt
import io
import json
import os
from pathlib import Path
from urllib import parse, request
from xml.etree import ElementTree as ET

from flows_engine import evaluate
from kis_short_sales import collect as kis_short_sales
from naver_public_flows import collect as naver_investors
from kiwoom_flows import collect_if_connected as kiwoom_investors
from kiwoom_short_lending import fetch_short_lending as kiwoom_short_lending

BASE = Path(__file__).resolve().parent
DATA = BASE / 'data'
IMPORTS = BASE / 'imports'
TICKER = '278470'
KRX_FLOW_URL = 'https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd?screenId=MDCSTAT023'
KRX_SHORT_URL = 'https://data.krx.co.kr/contents/MDC/STAT/srt/MDCSTAT300.jsp'
KSD_API_URL = 'https://apis.data.go.kr/B552481/SlbSvc/getSlbDealingByIsin'

INVESTOR_MAP = {
    'personal_krw': ('개인',),
    'foreign_krw': ('외국인', '기타외국인'),
    'institution_krw': ('금융투자','보험','투신','사모','은행','기타금융','연기금'),
    'pension_krw': ('연기금','연기금 등')
}
# Allow both official English-key file imports and source-form KRX aliases.
INVESTOR_KEYS = ('individual','foreign','institution','pension')


def save(path, obj):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2)+'\n',
                    encoding='utf-8')


def read(path, fallback):
    try:
        return json.loads(path.read_text(encoding='utf-8'))
    except (OSError, ValueError, TypeError):
        return fallback


def valid_date(x):
    if x is None:
        return None
    try:
        return dt.date.fromisoformat(str(x)[:10].replace('/','-')).isoformat()
    except ValueError:
        try:
            return dt.datetime.strptime(str(x)[:8],'%Y%m%d').date().isoformat()
        except ValueError:
            return None


def sum_group(row, columns):
    # All columns must be available: do not incorrectly equate missing
    # institution subcategories with zero net purchases.
    values=[]
    for name in columns:
        if name not in row:
            return None
        value=row[name]
        if value is None or value=='':
            return None
        try:
            values.append(int(str(value).replace(',','')))
        except ValueError:
            return None
    return sum(values)


def normalize_investor_dataframe(df, detail=True):
    """Map detailed or basic KRX net trade VALUE (KRW), not share counts."""
    if df is None or getattr(df,'empty',True):
        return []
    result=[]
    for day, values in df.iterrows():
        item=values.to_dict()
        date=valid_date(day.strftime('%Y-%m-%d') if hasattr(day,'strftime') else day)
        if not date:
            continue
        individual=sum_group(item,('개인',))
        # Basic group totals are official when explicitly present.
        # Avoid summing foreign twice when "외국인합계" is provided.
        foreign=(sum_group(item,('외국인합계',))
                 if '외국인합계' in item
                 else sum_group(item,('외국인','기타외국인')))
        pension_key='연기금' if '연기금' in item else '연기금 등'
        pension=sum_group(item,(pension_key,))
        institution=(sum_group(item,('기관합계',))
                     if '기관합계' in item
                     else sum_group(item,('금융투자','보험','투신','사모',
                                         '은행','기타금융',pension_key)))
        # Strict: if a detail column is missing, hold the entire category.
        result.append({'date':date,'individual':individual,
                       'foreign':foreign,'institution':institution,
                       'pension':pension,
                       'source':('KRX investor-by-security detailed net value (pykrx)' if detail
                                 else 'KRX investor-by-security basic net value (pykrx)'),
                       'unit':'KRW','record_status':'primary',
                       'institution_subgroup_covered':pension is not None})
    return result


def normalize_short_dataframe(df, prices):
    if df is None or getattr(df,'empty',True):
        return []
    by_date={r['date']:r for r in prices if r.get('date')}
    result=[]
    for day, row in df.iterrows():
        item=row.to_dict()
        date=valid_date(day.strftime('%Y-%m-%d') if hasattr(day,'strftime') else day)
        if not date:
            continue
        def integer(key):
            val=item.get(key)
            if val is None or val=='':
                return None
            try:
                return int(str(val).replace(',',''))
            except ValueError:
                return None
        short_qty=integer('공매도')
        short_value=integer('공매도금액')
        balance_qty=integer('잔고')
        balance_won=integer('잔고금액')
        p=by_date.get(date,{})
        value_proxy=(p.get('close_krw') or 0)*(p.get('volume') or 0)
        est=short_value/value_proxy*100 if short_value is not None and value_proxy>0 else None
        if any(v is not None for v in (short_qty,short_value,balance_qty,balance_won)):
            result.append({
                'date':date,
                'short_trade_qty':short_qty,'short_trade_value_krw':short_value,
                'reported_net_short_balance_qty':balance_qty,
                'reported_net_short_balance_krw':balance_won,
                'short_value_ratio_pct':round(est,3) if est is not None else None,
                'ratio_estimated_from_close_volume':est is not None,
                'source':'KRX individual short trading and reportable short-interest history',
                'note':'공매도 순보유잔고는 T+2 보고, 대차잔고와 같지 않음'
            })
    return result


def _numbers_for_isin(isin):
    return ''.join(str(ord(c)-55) if c.isalpha() else c for c in isin)


def get_isin(ticker=TICKER):
    """ISO6166 Luhn check digit; validates known KRX ticker mapping."""
    stem='KR7'+ticker+'00'
    chars=_numbers_for_isin(stem)
    # The check digit is appended on the right before Luhn validation,
    # so the rightmost existing character is doubled.
    total=0
    for idx,c in enumerate(reversed(chars)):
        digit=int(c)* (2 if idx%2==0 else 1)
        total += digit//10+digit%10
    return stem+str((-total)%10)


def _ksd_parse(xml):
    """Accept only explicitly labeled quantities from the stock-specific rows.

    A missing KSD field stays NULL; never infer repayment as a decrease in
    outstanding borrowed stock or infer short covering from repayment.
    """
    tree=ET.fromstring(xml)
    out=[]
    def val(obj, options):
        for key in options:
            text=obj.findtext('.//'+key)
            if text is not None and str(text).strip():
                try:
                    return int(str(text).replace(',',''))
                except ValueError:
                    return None
        return None
    for item in tree.findall('.//item'):
        date=valid_date(item.findtext('basDt') or item.findtext('trdDd')
                        or item.findtext('baseDate'))
        if not date:
            continue
        isincd=item.findtext('isinCd') or item.findtext('isin')
        if isincd and isincd!=get_isin():
            continue
        new=val(item,('lndQty','lendQty','lendngQty','newLendQty'))
        repaid=val(item,('rtnQty','rtrnQty','redmQty','returnQty'))
        balance=val(item,('balQty','lndBalQty','lendBalQty','stckLendBalQty'))
        if all(x is None for x in (new,repaid,balance)):
            continue
        out.append({'date':date,'new_qty':new,'returned_qty':repaid,
                    'balance_qty':balance,'source':'KSD SLB official API',
                    'unit':'shares'})
    return out


def read_ksd(key, base_date=None):
    if not key:
        return [],'KSD_SLB_API_KEY 미등록 · 대차 신규/상환/잔고 미확인'
    q={
        'serviceKey':parse.unquote(key),
        'isinCd':get_isin(),
        'numOfRows':100,'pageNo':1
    }
    if base_date:
        q['basDt']=base_date.replace('-','')
    url=KSD_API_URL+'?'+parse.urlencode(q)
    req=request.Request(url,headers={'Accept':'application/xml','User-Agent':'APR-SIGNAL data research'})
    with request.urlopen(req, timeout=14) as r:
        rows=_ksd_parse(r.read())
    if not rows:
        return [],'KSD 응답은 수신했지만 APR 종목별 신규/상환/잔고 수치 매핑 미확인'
    return rows,None


def read_imports(path, keys):
    """User-provided source-tagged CSVs, only complete and dated rows."""
    if not path.exists():
        return []
    rows=[]
    with path.open('r',encoding='utf-8-sig',newline='') as f:
        for raw in csv.DictReader(f):
            day=valid_date(raw.get('date'))
            if not day or not raw.get('source_url','').startswith('https://'):
                continue
            row={'date':day,'source':raw['source_url'],
                 'record_status':'manual_source_linked_unverified'}
            for name in keys:
                val=raw.get(name,'')
                try:
                    row[name]=int(val.replace(',','')) if val!='' else None
                except ValueError:
                    row[name]=None
            if any(row.get(name) is not None for name in keys):
                rows.append(row)
    return rows


def merge_by_date(previous, new):
    # Verified entries only. Newly fetched fields replace matching old keys
    # when not null; an observed zero is a real value (not a missing sentinel).
    out={x['date']:dict(x) for x in previous if x.get('date')}
    for row in new:
        if not row.get('date'):
            continue
        day=row['date']
        old=out.get(day,{})
        out[day]={**old,**{k:v for k,v in row.items() if v is not None}}
    return [out[day] for day in sorted(out)][-400:]


def collect():
    prior=read(DATA/'flows.json',{})
    market=read(DATA/'market.json',{})
    technical=read(DATA/'technical.json',{})
    prices=market.get('series') or []
    start=(dt.date.today()-dt.timedelta(days=255)).strftime('%Y%m%d')
    end=dt.date.today().strftime('%Y%m%d')
    issues=[]
    daily=list(prior.get('daily',[]))
    shorts=list(prior.get('short_daily',[]))
    lending=list(prior.get('lending_daily',[]))
    krx_ok=False
    krx_mode=None
    diagnostics={}
    try:
        from pykrx import stock
        try:
            d=stock.get_market_trading_value_by_date(start,end,TICKER,detail=True)
            diagnostics['detail_rows']=len(d) if d is not None else 0
            diagnostics['detail_columns']=list(map(str,d.columns))[:15] if d is not None else []
            new=normalize_investor_dataframe(d,detail=True)
            if not any(x.get('foreign') is not None
                       and x.get('institution') is not None for x in new):
                raise ValueError('KRX investor detail columns/rows missing')
            krx_mode='detailed'
        except Exception as detail_error:
            diagnostics['detail_error_type']=type(detail_error).__name__
            # Re-query the official KRX basic group view, rather than
            # wrongly interpreting absent detailed pension rows as zero.
            d=stock.get_market_trading_value_by_date(start,end,TICKER,detail=False)
            diagnostics['basic_rows']=len(d) if d is not None else 0
            diagnostics['basic_columns']=list(map(str,d.columns))[:10] if d is not None else []
            new=normalize_investor_dataframe(d,detail=False)
            if not any(x.get('foreign') is not None
                       and x.get('institution') is not None for x in new):
                raise ValueError('KRX basic group data unavailable too')
            krx_mode='basic_no_pension'
        daily=merge_by_date(daily,new)
        krx_ok=True
    except (Exception, ImportError) as exc:
        issues.append('KRX 상세·기본 수급: '+type(exc).__name__+' · 이전 검증값 유지')
    try:
        from pykrx import stock
        d=stock.get_shorting_status_by_date(start,end,TICKER)
        new=normalize_short_dataframe(d,prices)
        if not new:
            raise ValueError('KRX short-sale response empty or columns changed')
        shorts=merge_by_date(shorts,new)
    except (Exception, ImportError) as exc:
        issues.append('KRX 종목별 공매도/잔고: '+type(exc).__name__+' · 이전 검증값 유지')
    # KIS free read-only daily short-selling TR FHPST04830000.
    # Unlike KRX marketplace scraping, KIS is operational from GitHub
    # runners once optional production KIS credentials are configured.
    # KIS does NOT supply reported net short balances.
    kis_key_present=bool(os.environ.get('KIS_APP_KEY')) and bool(
        os.environ.get('KIS_APP_SECRET'))
    kis_result={'status':'not_configured','rows':0,'calls':0}
    if kis_key_present:
        try:
            kis_short_rows,kis_result=kis_short_sales(prices)
            if kis_short_rows:
                shorts=merge_by_date(shorts,kis_short_rows)
            if kis_result.get('status') != 'ok':
                issues.append('KIS 공매도 일별거래: '+
                              str(kis_result.get('status','미확인'))+
                              ' · 구체적 수치 미확인 날짜는 공란')
        except Exception as exc:
            kis_result={'status':'failed','error_type':type(exc).__name__,
                        'rows':0,'calls':0}
            issues.append('KIS 공매도 일별거래: '+type(exc).__name__+
                          ' · 이전 검증값 유지')
    # Read-only licensed securities API, if the user supplied app credentials
    # via GitHub Secrets. No user account/balance/trade/order API is called.
    kiwoom_key_present=bool(os.environ.get('KIWOOM_APP_KEY')) and bool(
        os.environ.get('KIWOOM_SECRET_KEY'))
    # GH-hosted runners use unpredictable public IPs; repeated OAuth requests
    # from unregistered IPs are futile and could trigger brokerage protection.
    # Credentials may remain stored; API calls need an explicitly enabled,
    # separately authorized environment with an IP matching Kiwoom's list.
    kiwoom_enabled=(kiwoom_key_present and
                    os.environ.get('KIWOOM_ALLOW_DYNAMIC_IP') == '1')
    kiwoom_meta={'status':('disabled_dynamic_runner_ip' if kiwoom_key_present
                           else 'not_configured'),'pages':0,'truncated':False}
    if kiwoom_enabled:
        try:
            kiwoom_rows, kiwoom_meta=kiwoom_investors(prices)
            if kiwoom_rows:
                # Kiwoom ka10059 gives individual, foreign, institution and
                # pension individually. Pension is included in institution.
                daily=merge_by_date(daily,kiwoom_rows)
            else:
                issues.append('Kiwoom ka10059: 일간 수급 미확인 · 이전값 유지')
            if kiwoom_meta.get('truncated'):
                issues.append('Kiwoom ka10059: 페이지 제한으로 과거 이력 일부만 수집')
        except Exception as exc:
            # NEVER log auth response, original HTTP error text or credentials.
            kiwoom_meta={'status':'failed','error_type':type(exc).__name__,
                         'pages':0,'truncated':False}
            issues.append('Kiwoom 투자주체 수급: '+type(exc).__name__+
                          ' · 이전값 유지 (키·토큰은 공개 안 함)')
    kiwoom_short_lending_meta={
        'short':{'status':('disabled_dynamic_runner_ip' if kiwoom_key_present else 'not_configured')},
        'lending':{'status':('disabled_dynamic_runner_ip' if kiwoom_key_present else 'not_configured')}
    }
    if kiwoom_enabled:
        try:
            kshort, klend, kiwoom_short_lending_meta=kiwoom_short_lending(
                os.environ['KIWOOM_APP_KEY'],
                os.environ['KIWOOM_SECRET_KEY'], prices)
            if kshort:
                shorts=merge_by_date(shorts,kshort)
            if klend:
                lending=merge_by_date(lending,klend)
            for key in ('short','lending'):
                meta=kiwoom_short_lending_meta.get(key,{})
                if meta.get('status') not in ('ok',):
                    issues.append('Kiwoom '+key+' 자료: '+
                                  str(meta.get('status','미확인'))+
                                  ' · 기존 검증값 유지')
        except Exception as exc:
            kiwoom_short_lending_meta={
                'short':{'status':'failed','error_type':type(exc).__name__},
                'lending':{'status':'failed','error_type':type(exc).__name__}}
            issues.append('Kiwoom 공매도·대차: '+type(exc).__name__+
                          ' (키·토큰은 노출하지 않음)')
    ksd_key=os.environ.get('KSD_SLB_API_KEY','')
    try:
        new,msg=read_ksd(ksd_key,base_date=prices[-1]['date'] if prices else None)
        if msg and not lending:
            issues.append(msg)
        if new:
            # KSD official values take precedence over broker-supplied lending
            # for the same day when both were independently verified.
            lending=merge_by_date(lending,new)
    except Exception as exc:
        issues.append('KSD 대차 API: '+type(exc).__name__+' · 이전값 유지')
    # Unauthenticated, read-only Naver public stock-page investor trend.
    # Source values are KR X net SHARES and the legacy net_krw fields are
    # explicitly tagged estimated (shares x the Naver KRX close).
    # Never overwrite more authoritative actual cash-value rows.
    naver_meta={'status':'unavailable','rows':0,'pages':0}
    if prices:
        try:
            naver_rows,naver_meta=naver_investors(prices[-1]['date'])
            by_day={x['date']:x for x in daily if x.get('date')}
            additions=[]
            for item in naver_rows:
                old=by_day.get(item['date'],{})
                if old and old.get('record_status') not in (
                    None,'public_website_derived_estimate'):
                    continue
                additions.append(item)
            if additions:
                daily=merge_by_date(daily,additions)
            if not naver_rows:
                issues.append('네이버 공개 KRX 수급: 조회 실패 · 이전 기록 유지')
            elif naver_meta.get('status')!='ok':
                issues.append('네이버 공개 KRX 수급: 일부 기간만 수신 · 수치 검증 필요')
        except Exception as exc:
            naver_meta={'status':'failed','error_type':type(exc).__name__,
                        'rows':0,'pages':0}
            issues.append('네이버 공개 KRX 수급: '+type(exc).__name__+
                          ' · 이전 기록 유지')
    imports={
      'daily': read_imports(IMPORTS/'apr_investor_daily.csv',INVESTOR_KEYS),
      'short': read_imports(IMPORTS/'apr_short_daily.csv',
          ('short_trade_qty','short_trade_value_krw','reported_net_short_balance_qty',
           'reported_net_short_balance_krw')),
      'lending': read_imports(IMPORTS/'apr_lending_daily.csv',
          ('new_qty','returned_qty','balance_qty'))
    }
    daily=merge_by_date(daily,imports['daily'])
    shorts=merge_by_date(shorts,imports['short'])
    lending=merge_by_date(lending,imports['lending'])
    analysis=evaluate(prices,daily,shorts,lending,technical.get('series') or [])
    now=dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')
    result={
       **analysis,
       'checked_at_utc':now,
       'data_status':{
           'krx_investor_live_ok':krx_ok,
           'kis_short_key_configured':kis_key_present,
           'kis_short_daily_result':kis_result,
           'fsc_stock_lending_key_configured':bool(os.environ.get('FSC_STOCK_LENDING_API_KEY')),
           'fsc_lending_status':('needs_endpoint_mapping' if os.environ.get('FSC_STOCK_LENDING_API_KEY')
                                 else 'not_configured'),
           'kiwoom_app_configured':kiwoom_key_present,
           'kiwoom_enabled_for_host':kiwoom_enabled,
           'kiwoom_read_only_result':kiwoom_meta,
           'naver_public_result':naver_meta,
           'naver_flow_is_estimated':any(x.get('amount_estimated') for x in daily),
           'kiwoom_short_lending_result':kiwoom_short_lending_meta,
           'krx_investor_mode':krx_mode,
           'krx_collection_diagnostics':diagnostics,
           'ksd_api_key_present':bool(ksd_key),
           'last_verified_flow_date':analysis.get('flow_last_date'),
           'primary_source':'KRX detailed investor-by-security transactions',
           'flow_source_url':KRX_FLOW_URL,
           'short_source_url':KRX_SHORT_URL,
           'lending_source_url':'https://www.data.go.kr/data/15157426/openapi.do',
           'issues':issues,
           'warning':('KRX 범위와 NXT 포함 여부·거래시간 구분을 원천 자료와 대조. '
                      '단위는 순매수 거래대금(원), 연기금은 기관 합계의 부분집합')
       },
       'daily':daily,'short_daily':shorts,'lending_daily':lending
    }
    save(DATA/'flows.json',result)
    print(json.dumps({
       'flow_asof':analysis.get('flow_last_date'),
       'price_asof':analysis.get('price_last_date'),
       'aligned':analysis.get('price_aligned'),
       'flow_rows':len(daily),'short_rows':len(shorts),'lending_rows':len(lending),
       'krx_live_ok':krx_ok,'kis_short_status':kis_result.get('status'),
       'fsc_lending_key_present':bool(os.environ.get('FSC_STOCK_LENDING_API_KEY')),
       'naver_status':naver_meta.get('status'),
       'naver_records':naver_meta.get('rows'),'kiwoom_connected':kiwoom_key_present,
       'kiwoom_status':kiwoom_meta.get('status'),
       'kiwoom_short_status':kiwoom_short_lending_meta.get('short',{}).get('status'),
       'kiwoom_lending_status':kiwoom_short_lending_meta.get('lending',{}).get('status'),
       'ksd_key_present':bool(ksd_key),
       'issues':issues
    },ensure_ascii=False))
    return result


if __name__=='__main__':
    collect()
