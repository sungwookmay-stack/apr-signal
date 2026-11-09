"""Read-only Kiwoom REST short-sale TR ka10014 and lending TR ka20068.

No account info, balances, personal trading, or order endpoints are used.
- ka10014 'ovr_shrts_qty' is cumulative traded shares, NOT short interest.
- ka10014 does NOT report outstanding short-position balance.
- ka20068 'rmnd' is outstanding BORROWED STOCK, NOT net short interest.
- ka20068 'dbrt_trde_rpy' is loan repayment, NOT proven short covering.
- Short volume ratio = shares short sold / all shares traded for the SAME DAY.
  This is NOT short trade VALUE ratio.
Never fill unidentified data as zero or claim short balance from a loan.
"""
from __future__ import annotations

import datetime as dt

from kiwoom_flows import (
    HOST, STOCK, _http_post, _to_integer, _date, _success, get_token
)

SHORT_URL = HOST + "/api/dostk/shsa"
LENDING_URL = HOST + "/api/dostk/slb"


def _signed_number(x):
    if x is None:
        return None
    try:
        return float(str(x).strip().replace(",",""))
    except (ValueError, TypeError):
        return None


def _filter_rows(data, collection, permit_dates):
    result = data.get(collection) if isinstance(data,dict) else None
    if not isinstance(result,list):
        raise ValueError("Provider response lacks expected dated collection")
    dates = set(permit_dates or [])
    return [row for row in result if isinstance(row,dict)
            and _date(row.get('dt')) in dates]


def short_rows(response, permitted_dates):
    """Normalize *short SALE TRADING* only. Balance remains unknown."""
    out={}
    for row in _filter_rows(response, "shrts_trnsn", permitted_dates):
        day=_date(row.get('dt'))
        short=_to_integer(row.get('shrts_qty'))
        alltraded=_to_integer(row.get('trde_qty'))
        if short is None or alltraded is None or alltraded<=0 or short<0 or short>alltraded:
            continue
        # Preserve per-day numerator and denominator to audit computed ratio.
        out[day]={
            'date':day,'short_trade_qty':short,
            'total_traded_qty':alltraded,
            'short_volume_ratio_pct':round(short/alltraded*100,3),
            'short_value_ratio_pct':None,
            'short_trade_value_krw':None,  # provider units unverified, no guessing
            'reported_net_short_balance_qty':None,
            'source':'Kiwoom REST ka10014 /api/dostk/shsa',
            'source_quality':'broker_market_data',
            'ratio_method':'daily_short_qty_over_total_trade_qty',
            'note':'당일 공매도 체결수량/당일 거래량; 누적 공매도량은 잔고 아님'
        }
    return [out[k] for k in sorted(out)]


def lending_rows(response, permitted_dates):
    """Normalize stock-lending contract, repayment, and BORROWED balance."""
    out={}
    for row in _filter_rows(response, "dbrt_trde_trnsn", permitted_dates):
        day=_date(row.get('dt'))
        new=_to_integer(row.get('dbrt_trde_cntrcnt'))
        returned=_to_integer(row.get('dbrt_trde_rpy'))
        outstanding=_to_integer(row.get('rmnd'))
        if all(x is None for x in (new, returned, outstanding)):
            continue
        if any(x is not None and x < 0 for x in (new, returned, outstanding)):
            continue
        out[day]={
            'date':day,
            'new_qty':new,'returned_qty':returned,'balance_qty':outstanding,
            'source':'Kiwoom REST ka20068 /api/dostk/slb',
            'unit':'shares','source_quality':'broker_market_data',
            'note':'대차 잔고 ≠ 공매도 순보유잔고, 상환 ≠ 숏커버 확정'
        }
    return [out[k] for k in sorted(out)]


def _pages(token, api_id, url, body, list_name, convert,
           market_days, post=_http_post, max_pages=5):
    rows={}
    cont, cursor="N",""
    attempts=0
    truncated=False
    while attempts<max_pages:
        payload,headers=post(url,body,{
            'authorization':'Bearer '+token,
            'api-id':api_id,
            'cont-yn':cont,
            'next-key':cursor
        })
        if not _success(payload):
            raise RuntimeError(api_id+" unavailable or returned application error")
        if not isinstance(payload.get(list_name),list):
            raise ValueError(api_id+" data list missing")
        attempts+=1
        for row in convert(payload,market_days):
            rows[row['date']]=row
        lower={str(k).lower():v for k,v in (headers or {}).items()}
        if str(lower.get('cont-yn','N')).upper()!='Y':
            break
        cursor=str(lower.get('next-key',''))
        if not cursor or attempts>=max_pages:
            truncated=True
            break
        cont="Y"
    return [rows[k] for k in sorted(rows)],{
        'status':('partial_pagination' if truncated else
                  'ok' if rows else 'empty_rows'),
        'pages':attempts,'truncated':truncated,
        'count':len(rows),'api_id':api_id,'read_only':True
    }


def fetch_short_lending(appkey,secretkey,prices,post=_http_post):
    """Use one short-lived token for two read-only public-market endpoints."""
    days=[x['date'] for x in prices if x.get('date')]
    if not days:
        return [],[],{'short':{'status':'no_price_dates'},
                     'lending':{'status':'no_price_dates'}}
    start=days[max(0,len(days)-120)].replace("-","")
    end=days[-1].replace("-","")
    token=get_token(appkey,secretkey,post=post)
    shorts,lending=[],[]
    report={}
    try:
        shorts,report['short']=_pages(
            token,"ka10014",SHORT_URL,{
                "stk_cd":STOCK,"strt_dt":start,"end_dt":end,"tm_tp":"1"
            },"shrts_trnsn",short_rows,days,post=post)
    except Exception as exc:
        report['short']={'status':'failed','error_type':type(exc).__name__}
    try:
        lending,report['lending']=_pages(
            token,"ka20068",LENDING_URL,{
                "stk_cd":STOCK,"strt_dt":start,"end_dt":end,"all_tp":"0"
            },"dbrt_trde_trnsn",lending_rows,days,post=post)
    except Exception as exc:
        report['lending']={'status':'failed','error_type':type(exc).__name__}
    return shorts,lending,report
