"""APR KIS Open API read-only short-trading collector (278470).

Official Korea Investment Securities reference:
koreainvestment/open-trading-api/examples_llm/domestic_stock/daily_short_sale
GET /uapi/domestic-stock/v1/quotations/daily-short-sale,
TR_ID FHPST04830000, daily rows in output2.
Does not provide reportable net short positions, stock lending, or repayment.
KIS_APP_KEY and KIS_APP_SECRET must only be supplied as GitHub Secrets.
No account balance, orders, or private portfolio endpoints are used.
"""
from __future__ import annotations

import calendar
import datetime as dt
import json
import math
import os
import re
from urllib import parse, request

HOST="https://openapi.koreainvestment.com:9443"
TOKEN_URL=HOST+"/oauth2/tokenP"
SHORT_URL=HOST+"/uapi/domestic-stock/v1/quotations/daily-short-sale"
TR_ID="FHPST04830000"
TICKER="278470"

def as_int(v):
    if v is None or isinstance(v,bool):
        return None
    s=str(v).strip().replace(",","")
    return int(s) if re.fullmatch(r"[+-]?\d+",s) else None

def value_ratio(row):
    """Dimensionless daily value ratio, never volume ratio or cumulative value.

    Absolute API amount units have not been live-verified, so do not publish
    those as KRW. Both daily amount fields share a unit; their ratio is safe.
    A conflict with the provider's rounded ratio quarantines only this metric.
    """
    def number(value):
        if value is None or isinstance(value, bool):
            return None
        try:
            n = float(str(value).replace(',', '').strip())
            return n if math.isfinite(n) else None
        except (ValueError, TypeError):
            return None
    short = number(row.get('ssts_tr_pbmn'))
    total = number(row.get('acml_tr_pbmn'))
    reported = number(row.get('ssts_tr_pbmn_rlim'))
    if reported is not None and not 0 <= reported <= 100:
        return None, 'invalid_reported_value_ratio'
    if short is not None and total is not None:
        if total <= 0 or short < 0 or short > total:
            return None, 'invalid_daily_value_pair'
        computed = short / total * 100
        if reported is not None and abs(computed - reported) > 0.02:
            return None, 'daily_value_ratio_conflict'
        return round(computed, 3), 'reported_daily_short_value_divided_by_daily_trade_value'
    return reported, ('provider_daily_value_ratio' if reported is not None
                      else 'daily_value_ratio_missing')

def norm_date(s):
    s=str(s or "").strip()
    if not re.fullmatch(r"20\d{6}",s):
        return None
    try:
        return dt.datetime.strptime(s,"%Y%m%d").date().isoformat()
    except ValueError:
        return None

def normalize(payload,allowed_days=None):
    if not isinstance(payload,dict) or str(payload.get("rt_cd"))!="0":
        return []
    raw=payload.get("output2")
    if not isinstance(raw,list):
        return []
    allowed=set(allowed_days) if allowed_days is not None else None
    today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    rows={}
    for row in raw:
        if not isinstance(row,dict):
            continue
        day=norm_date(row.get("stck_bsop_date"))
        if not day or day>today or (allowed is not None and day not in allowed):
            continue
        short=as_int(row.get("ssts_cntg_qty"))
        traded=as_int(row.get("acml_vol"))
        if short is None or traded is None or short<0 or traded<=0 or short>traded:
            continue
        amount_ratio, amount_ratio_method = value_ratio(row)
        rows[day]={
            "date":day,"short_trade_qty":short,
            "total_traded_qty":traded,
            "short_volume_ratio_pct":round(short/traded*100,3),
            "short_trade_value_krw":None,"short_value_ratio_pct":amount_ratio,
            "short_value_ratio_method":amount_ratio_method,
            "reported_net_short_balance_qty":None,
            "reported_net_short_balance_krw":None,
            "source":"KIS OpenAPI FHPST04830000 short-selling daily trades",
            "source_url":"https://apiportal.koreainvestment.com/docs",
            "record_status":"broker_market_data",
            "ratio_method":"short_sold_shares_divided_by_reported_trade_shares",
            "note":"공매도 수량비중·거래대금비중 구분. 절대 거래대금 단위 미검증으로 원화금액 미표시. 공매도 순보유잔고와 대차잔고는 미제공"
        }
    return [rows[k] for k in sorted(rows)]

def http_json(url,method="GET",headers=None,data=None):
    b=None if data is None else json.dumps(data).encode("utf8")
    req=request.Request(url,data=b,headers=headers or {},method=method)
    with request.urlopen(req,timeout=15) as r:
        if r.status!=200:
            raise RuntimeError("KIS HTTP status not 200")
        return json.loads(r.read(300000).decode("utf8"))

def token(key,secret,http=http_json):
    if not key or not secret:
        raise ValueError("KIS key pair missing")
    data=http(TOKEN_URL,method="POST",headers={
        "content-type":"application/json; charset=utf-8"
    },data={"grant_type":"client_credentials","appkey":key,"appsecret":secret})
    t=data.get("access_token") if isinstance(data,dict) else None
    if not isinstance(t,str) or len(t)<8:
        raise RuntimeError("KIS OAuth token unavailable")
    return t

def month_windows(start,end,max_windows=7):
    first=dt.date.fromisoformat(start)
    last=dt.date.fromisoformat(end)
    cur=last.replace(day=1)
    out=[]
    while cur>=first.replace(day=1) and len(out)<max_windows:
        last_month_day=calendar.monthrange(cur.year,cur.month)[1]
        stop=min(last,cur.replace(day=last_month_day))
        beg=max(first,cur)
        if beg<=stop:
            out.append((beg.strftime("%Y%m%d"),stop.strftime("%Y%m%d")))
        cur=(cur-dt.timedelta(days=1)).replace(day=1)
    return list(reversed(out))

def collect(price_rows,key=None,secret=None,http=http_json):
    key=key if key is not None else os.environ.get("KIS_APP_KEY","")
    secret=secret if secret is not None else os.environ.get("KIS_APP_SECRET","")
    if not key or not secret:
        return [],{"status":"not_configured","rows":0,"calls":0}
    dates=sorted({x["date"] for x in price_rows if x.get("date")})
    if not dates:
        return [],{"status":"no_price_dates","rows":0,"calls":0}
    try:
        bearer=token(key,secret,http=http)
        last=dt.date.fromisoformat(dates[-1])
        first=max(dt.date.fromisoformat(dates[0]),last-dt.timedelta(days=185))
        windows=month_windows(first.isoformat(),last.isoformat())
        saved,errors={},[]
        for beg,end in windows:
            query=parse.urlencode({
                "FID_COND_MRKT_DIV_CODE":"J",
                "FID_INPUT_ISCD":TICKER,
                "FID_INPUT_DATE_1":beg,
                "FID_INPUT_DATE_2":end
            })
            try:
                body=http(SHORT_URL+"?"+query,headers={
                    "authorization":"Bearer "+bearer,
                    "appkey":key,"appsecret":secret,
                    "tr_id":TR_ID,"custtype":"P"})
                if not isinstance(body,dict) or str(body.get("rt_cd"))!="0":
                    raise ValueError("KIS response not successful")
                items=normalize(body,allowed_days=dates)
                if not items:
                    errors.append("no_valid_daily_data_"+beg[:6])
                for item in items:
                    saved[item["date"]]=item
            except Exception as exc:
                errors.append(type(exc).__name__+"_"+beg[:6])
        result=[saved[k] for k in sorted(saved)]
        return result,{
            "status":"ok" if result and not errors else "partial" if result else "unavailable",
            "rows":len(result),"calls":len(windows),"errors":errors,
            "last":result[-1]["date"] if result else None,
            "unit":"shares","api_id":TR_ID,
            "reportable_net_short_balance_available":False}
    except Exception as exc:
        return [],{"status":"failed","error_type":type(exc).__name__,
                   "rows":0,"calls":0}
