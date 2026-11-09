"""FSC stock-specific securities-lending public data API: APR 278470.

Verified 2026-11-10 against data.go.kr's embedded Swagger (dataset 15059612):
 Base: https://apis.data.go.kr/1160100/GetStocLendBorrInfoService_V2
 GET /getStItemLendAndBorrStatu_V2
 Required: serviceKey, resultType, numOfRows, pageNo
 Optional filters: basDt (YYYYMMDD), isinCdNm (security name)
 Response fields: basDt, isinCd, isinCdNm, lnbCclStckCnt,
                  lnbRdptStckCnt, lnbRmanStckCnt

FSC public data are updated after 13:00 the NEXT business day. The FSC data
are NOT short positions. Missing/unauthorized data never become zero.
Keep serviceKey private: never log full URL or HTTP exception messages.
"""
from __future__ import annotations
import datetime as dt
import json
import os
import re
from pathlib import Path
from urllib import parse, request, error
from xml.etree import ElementTree as ET

API_URL=("https://apis.data.go.kr/1160100/GetStocLendBorrInfoService_V2/"
         "getStItemLendAndBorrStatu_V2")
SERVICE_PAGE="https://www.data.go.kr/data/15059612/openapi.do"
ISIN="KR7278470000"
NAME="에이피알"

def amount(x):
    if x is None or isinstance(x,bool):
        return None
    val=str(x).replace(",","").strip()
    return int(val) if re.fullmatch(r"\d+",val) else None

def date_str(x):
    if x is None:return None
    val=str(x).strip()
    if re.fullmatch(r"20\d{6}",val):
        try:return dt.datetime.strptime(val,"%Y%m%d").date().isoformat()
        except ValueError:return None
    if re.fullmatch(r"20\d{2}-\d{2}-\d{2}",val):
        try:return dt.date.fromisoformat(val).isoformat()
        except ValueError:return None
    return None

def _find_rows(node):
    if not isinstance(node,dict):
        return []
    wrapper=node.get("response",node)
    if not isinstance(wrapper,dict):
        return []
    header=wrapper.get("header")
    if isinstance(header,dict):
        code=header.get("resultCode")
        if code is not None and str(code) not in ("00","0","0000"):
            raise ValueError("FSC API business error")
    body=wrapper.get("body")
    if not isinstance(body,dict):
        return []
    items=body.get("items")
    if isinstance(items,dict):
        items=items.get("item")
    if isinstance(items,dict):
        items=[items]
    return items if isinstance(items,list) else []

def normalize(payload,allowed_dates=None):
    """Strict stock identity and unit checks, no cross-ticker contamination."""
    allowed=set(allowed_dates) if allowed_dates is not None else None
    out=[]
    for r in _find_rows(payload):
        if not isinstance(r,dict):
            continue
        day=date_str(r.get("basDt"))
        if not day or (allowed is not None and day not in allowed):
            continue
        code=str(r.get("isinCd") or "").strip()
        name=str(r.get("isinCdNm") or "").strip()
        if code:
            if code!=ISIN:continue
        elif not name.startswith(NAME):
            continue
        new=amount(r.get("lnbCclStckCnt"))
        returned=amount(r.get("lnbRdptStckCnt"))
        balance=amount(r.get("lnbRmanStckCnt"))
        if all(n is None for n in (new,returned,balance)):
            continue
        out.append({
            "date":day,
            "new_qty":new,
            "returned_qty":returned,
            "balance_qty":balance,
            "source":"Financial Services Commission public stock lending API 15059612",
            "source_url":SERVICE_PAGE,
            "record_status":"official_public_api_noncommercial",
            "unit":"shares",
            "note":"체결·상환·잔고는 대차정보. 공매도 거래·순보유잔고가 아님"
        })
    return out

def _xml_payload(data):
    root=ET.fromstring(data)
    if root.tag=="OpenAPI_ServiceResponse":
        raise PermissionError("FSC authorization failed")
    for child in root.findall(".//header/resultCode"):
        if (child.text or "").strip() not in ("00","0","0000"):
            raise ValueError("FSC response error code")
    arr=[]
    for item in root.findall(".//items/item"):
        arr.append({p.tag:p.text for p in item})
    return {"response":{"body":{"items":{"item":arr}}}}

def get_for_day(day,key,http=None):
    """Single read-only request, no secret in diagnostics."""
    if not key:
        raise ValueError("FSC key missing")
    args={
        "serviceKey":parse.unquote(key),
        "numOfRows":"50","pageNo":"1","resultType":"json",
        "basDt":day.replace("-",""),"isinCdNm":NAME
    }
    url=API_URL+"?"+parse.urlencode(args)
    if http is None:
        def http(url):
            req=request.Request(url,headers={
                "User-Agent":"APR-SIGNAL noncommercial research",
                "Accept":"application/json,application/xml"})
            with request.urlopen(req,timeout=14) as r:
                return r.read(120000)
    raw=http(url)
    if isinstance(raw,dict):
        payload=raw
    elif raw.lstrip().startswith(b"<"):
        payload=_xml_payload(raw)
    else:
        payload=json.loads(raw.decode("utf8","replace"))
    return normalize(payload,allowed_dates={day})

def collect(price_rows,previous_rows=None,key=None,http=None,max_days=8):
    """Only query eligible prior trading sessions, backfill up to 8/day."""
    key=key if key is not None else os.environ.get(
        "FSC_STOCK_LENDING_API_KEY","")
    if not key:
        return [],{"status":"not_configured","queries":0,"rows":0}
    today=dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    saved={r["date"] for r in (previous_rows or []) if r.get("date")}
    price_days=sorted({r["date"] for r in price_rows
                       if r.get("date") and r["date"]<today})
    # Always re-check the last two eligible market sessions for corrections,
    # and extend history from newest missing dates toward older ones.
    latest=price_days[-2:]
    missing=[d for d in price_days[-100:] if d not in saved]
    dates=sorted(set((missing[-max_days:]+latest)))[-max_days:]
    if not dates:
        return [],{"status":"no_eligible_dates","queries":0,"rows":0}
    out={}
    checks=0
    errors=[]
    for day in dates:
        checks+=1
        try:
            entries=get_for_day(day,key,http=http)
            for row in entries:
                out[row["date"]]=row
        except error.HTTPError as exc:
            # HTTPError.url includes secret serviceKey! Never print it.
            if exc.code in (401,403):
                errors.append("authorization_http_"+str(exc.code))
                break
            errors.append("http_"+str(exc.code))
        except PermissionError:
            errors.append("authorization_denied")
            break
        except Exception as exc:
            errors.append(type(exc).__name__)
    rows=[out[d] for d in sorted(out)]
    return rows,{
        "status":("authorization_denied" if
                  any(x.startswith("authorization") for x in errors) else
                  "ok" if rows and not errors else
                  "partial" if rows else "no_verified_rows"),
        "queries":checks,"rows":len(rows),"date_last":rows[-1]["date"] if rows else None,
        "errors":errors[:8],
        "source_update_lag":"next_business_day_after_13_kst",
        "source_url":SERVICE_PAGE,
        "license":"KOGL_type2_source_attribution_noncommercial"
    }
