#!/usr/bin/env python3
"""Read-only, unauthenticated APR investor trend from Naver's public finance UI.

2026-11-09 GitHub-hosted-runner live probe confirmed:
 https://m.stock.naver.com/front-api/stock/domestic/trend?code=278470
 JSON {isSuccess: true, result: {items:[{localTradedAt,krx:{...},nxt:...}],
 hasNext:true,cursor:"opaque"}}.
Pagination: ?code=278470&cursor=<opaque>; neither page=2 nor pageSize=60
changes the first 10 records.

CRITICAL: KRX foreignNetVolume/organizationNetVolume/individualNetVolume
are *SHARES* (not KRW). We also preserve those source volumes unchanged.
For compatibility with the old value-oriented flows engine we estimate
KRW=net_shares*KRX daily closingPrice. This is NOT actual net cash trading.
KRX-only investor types do NOT provide pensions: always null.

This endpoint is NOT a supported official Naver API and can change or be
blocked. Fetch ≤9 pages once or twice daily, no browser automation, account,
login, cookie, personal data, key, IP restriction, or paid API.
"""
from __future__ import annotations
import datetime as dt
import json
import re
from urllib import parse, request

URL = "https://m.stock.naver.com/front-api/stock/domestic/trend"
SOURCE_PAGE = "https://stock.naver.com/domestic/stock/278470/investmentinfo"
ORIGIN = "Naver Finance public investor trend (unofficial internal endpoint)"
TICKER = "278470"
ACTOR_COLUMNS = {
    "foreign": ("foreignNetVolume", "foreignBuyVolume", "foreignSellVolume"),
    "institution": ("organizationNetVolume", "organizationBuyVolume",
                    "organizationSellVolume"),
    "individual": ("individualNetVolume", "individualBuyVolume",
                   "individualSellVolume"),
}


def int_field(x):
    if x is None or isinstance(x, bool):
        return None
    if isinstance(x, int):
        return x
    s = str(x).replace(",", "").strip()
    return int(s) if re.fullmatch(r"[+-]?\d+", s) else None


def valid_day(x):
    if not isinstance(x, str) or not re.fullmatch(r"20\d{2}-\d{2}-\d{2}", x):
        return None
    try:
        return dt.date.fromisoformat(x).isoformat()
    except ValueError:
        return None


def normalize(payload, latest_date=None):
    """Convert dated public KRX shares to tagged estimated cash amounts."""
    if not isinstance(payload, dict) or payload.get("isSuccess") is not True:
        return []
    result = payload.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("items"), list):
        return []
    now_kst = dt.datetime.now(dt.timezone(dt.timedelta(hours=9))).date().isoformat()
    rows = []
    for obj in result["items"]:
        if not isinstance(obj, dict):
            continue
        day = valid_day(obj.get("localTradedAt"))
        if not day or day > now_kst or (latest_date and day > latest_date):
            continue
        krx = obj.get("krx")
        if not isinstance(krx, dict):
            continue
        price = int_field(krx.get("closingPrice"))
        volume = int_field(krx.get("tradingVolume"))
        if price is None or volume is None or price <= 0 or volume <= 0:
            continue
        actor_quantities = {}
        for actor, (net, buy, sell) in ACTOR_COLUMNS.items():
            net_qty = int_field(krx.get(net))
            buy_qty = int_field(krx.get(buy))
            sell_qty = int_field(krx.get(sell))
            # If buy/sell are available, a mismatching net amount is rejected
            # instead of silently accepting changed API column semantics.
            if (net_qty is not None and buy_qty is not None
                    and sell_qty is not None and buy_qty-sell_qty != net_qty):
                net_qty = None
            actor_quantities[actor] = net_qty
        if all(v is None for v in actor_quantities.values()):
            continue
        row = {
            "date": day, "individual":
                actor_quantities["individual"]*price
                if actor_quantities["individual"] is not None else None,
            "foreign":
                actor_quantities["foreign"]*price
                if actor_quantities["foreign"] is not None else None,
            "institution":
                actor_quantities["institution"]*price
                if actor_quantities["institution"] is not None else None,
            "pension": None,
            "individual_net_qty": actor_quantities["individual"],
            "foreign_net_qty": actor_quantities["foreign"],
            "institution_net_qty": actor_quantities["institution"],
            "pension_net_qty": None,
            "krx_close_krw": price,
            "krx_volume_shares": volume,
            "source": ORIGIN, "source_url": SOURCE_PAGE,
            "market_scope": "KRX_ONLY_NOT_NXT",
            "record_status": "public_website_derived_estimate",
            "unit": "KRW_ESTIMATED_NOT_ACTUAL",
            "amount_estimated": True,
            "amount_estimation": "individual net shares × KRX official-page close",
            "observed_at_utc": dt.datetime.now(
                dt.timezone.utc).isoformat(timespec="seconds"),
        }
        rows.append(row)
    return rows


def get_page(cursor=None, timeout=12, get_bytes=None):
    params = {"code": TICKER}
    if cursor:
        params["cursor"] = cursor
    url = URL + "?" + parse.urlencode(params)
    if get_bytes is None:
        def get_bytes(target, timeout):
            req = request.Request(target, headers={
                "User-Agent":
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/130.0 Safari/537.36",
                "Accept": "application/json,text/plain,*/*",
                "Referer": SOURCE_PAGE,
            })
            with request.urlopen(req, timeout=timeout) as r:
                if "json" not in r.headers.get("Content-Type","").lower():
                    raise ValueError("Naver endpoint returned non-JSON response")
                return r.read(300000)
    doc = json.loads(get_bytes(url,timeout=timeout).decode("utf-8"))
    if not isinstance(doc, dict) or doc.get("isSuccess") is not True:
        raise ValueError("Naver investor flow response was not successful")
    result = doc.get("result")
    if not isinstance(result, dict) or not isinstance(result.get("items"),list):
        raise ValueError("Naver response changed its investor rows schema")
    return doc


def collect(latest_date, get_bytes=None, max_pages=9, max_rows=90):
    """Small capped cursor-pagination collection, no hypothetical missing days."""
    if not valid_day(latest_date):
        return [], {"status":"missing_valid_price_date","pages":0,"rows":0}
    accumulated = {}
    cursor = None
    used = set()
    pages = 0
    errors = []
    full = False
    for _ in range(max_pages):
        try:
            doc = get_page(cursor,get_bytes=get_bytes)
            result = doc["result"]
            batch = normalize(doc, latest_date=latest_date)
            pages += 1
            for row in batch:
                accumulated[row["date"]] = row
            if not result.get("hasNext"):
                full = True
                break
            nxt = result.get("cursor")
            if not isinstance(nxt,str) or not nxt or nxt in used:
                errors.append("Missing or repeated opaque pagination cursor")
                break
            used.add(nxt)
            cursor = nxt
            if len(accumulated) >= max_rows:
                break
        except Exception as exc:
            errors.append(type(exc).__name__+" (Naver daily investor feed)")
            break
    rows = [accumulated[d] for d in sorted(accumulated)][-max_rows:]
    return rows, {
        "status":("ok" if len(rows)>=60 and not errors else
                  "partial" if rows else "unavailable"),
        "pages":pages,"rows":len(rows),
        "start":rows[0]["date"] if rows else None,
        "end":rows[-1]["date"] if rows else None,
        "has_full_history":full,
        "truncated":len(rows)>=max_rows or (not full),
        "latest_market_date":latest_date,
        "unit":"shares_original_KRW_close_times_shares_estimated",
        "market_scope":"KRX_ONLY_NOT_NXT",
        "pension_available":False,
        "issues":errors,
        "source_url":SOURCE_PAGE
    }
