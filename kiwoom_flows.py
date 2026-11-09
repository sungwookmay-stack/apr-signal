"""Read-only Kiwoom REST investor flow adapter for APR (278470).

OAuth (au10001) authenticates using KIWOOM_APP_KEY / KIWOOM_SECRET_KEY.
ka10059 POST /api/dostk/stkinfo returns daily KRW net-trading amounts
as MILLION KRW. The amount flag is 1; the side flag is 0 (net buy).
We convert to KRW using * 1_000_000, independently of quantity unit_tp.

Safe by design: GET/POST only to OAuth and stock information DATA endpoints.
No order endpoint, no access-token persistence, no secret in logs or JSON.
Never call "unknown/blank" pension fields 0. Exact as-of and provenance
required. Optional data never overrides more recently verified values.
"""
from __future__ import annotations

import datetime as dt
import json
import os
from urllib import request

HOST = "https://api.kiwoom.com"
TOKEN_URL = HOST + "/oauth2/token"
DAILY_URL = HOST + "/api/dostk/stkinfo"
TR_ID = "ka10059"
STOCK = "278470"
MILLION = 1_000_000
# Confirmed API field labels in Kiwoom REST ka10059:
NET_FIELDS = {
    "individual": "ind_invsr",
    "foreign": "frgnr_invsr",
    "institution": "orgn",
    "pension": "penfnd_etc",
}
SUBGROUP_FIELDS = {
    "financial_investment":"fnnc_invt",
    "insurance":"insrnc",
    "investment_trust":"invtrt",
    "other_finance":"etc_fnnc",
    "bank":"bank",
    "private_fund":"samo_fund",
    "national":"natn",
}


def _to_integer(value):
    """Treat omitted or blank fields as missing, never a valid zero."""
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        if int(value) == value:
            return int(value)
        return None
    txt = str(value).strip().replace(",", "").replace(" ", "")
    if not txt or txt in ("-", "+", "--", "N/A", "null"):
        return None
    if txt.startswith("--"):
        txt = "-" + txt[2:]
    if txt.startswith("++"):
        txt = "+" + txt[2:]
    if not txt.lstrip("+-").isdigit():
        return None
    return int(txt)


def _date(s):
    s = str(s or "").strip()
    try:
        if len(s)==8 and s.isdigit():
            return dt.datetime.strptime(s, "%Y%m%d").date().isoformat()
        return dt.date.fromisoformat(s).isoformat()
    except ValueError:
        return None


def normalize_daily(payload, permitted_dates=None):
    """Normalize a ka10059 daily observation list into confirmed KRW values."""
    if not isinstance(payload, dict):
        return []
    raw = payload.get("stk_invsr_orgn")
    if not isinstance(raw, list):
        return []
    allowed = set(permitted_dates) if permitted_dates is not None else None
    today = dt.date.today().isoformat()
    rows = {}
    for r in raw:
        if not isinstance(r, dict):
            continue
        day = _date(r.get("dt"))
        if not day or day > today or (allowed is not None and day not in allowed):
            continue
        # The issuer's group totals are already inclusive; pension is a subset.
        numbers = {key: _to_integer(r.get(field))
                   for key, field in NET_FIELDS.items()}
        if all(n is None for n in numbers.values()):
            continue
        row = {
            "date": day, "unit": "KRW",
            "source": "Kiwoom Securities REST ka10059 (exchange-scoped)",
            "record_status": "broker_public_market_data",
            "market_scope": "Kiwoom ka10059 stock market; confirm KRX/NXT scope",
            "amount_source_unit": "million_KRW",
            "individual": numbers["individual"]*MILLION
                          if numbers["individual"] is not None else None,
            "foreign": numbers["foreign"]*MILLION
                       if numbers["foreign"] is not None else None,
            "institution": numbers["institution"]*MILLION
                           if numbers["institution"] is not None else None,
            "pension": numbers["pension"]*MILLION
                       if numbers["pension"] is not None else None,
            "subgroups": {name: (_to_integer(r.get(field))*MILLION
                        if _to_integer(r.get(field)) is not None else None)
                        for name, field in SUBGROUP_FIELDS.items()}
        }
        rows[day] = row
    return [rows[k] for k in sorted(rows)]


def _http_post(url, body, headers=None, timeout=15):
    """Injectable HTTP client; never print token/key/body on failure."""
    payload = json.dumps(body, separators=(',',':')).encode("utf-8")
    h = {"Content-Type":"application/json;charset=UTF-8"}
    h.update(headers or {})
    req = request.Request(url, data=payload, headers=h, method="POST")
    with request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
        # Kiwoom response headers carry pagination.
        response_headers = {k.lower():v for k,v in resp.headers.items()}
    return json.loads(raw.decode("utf-8")), response_headers


def _success(response):
    if not isinstance(response, dict):
        return False
    val = response.get("return_code")
    return val is not None and str(val) == "0"


def get_token(appkey, secretkey, post=_http_post):
    if not appkey or not secretkey:
        raise ValueError("Kiwoom credentials are unavailable")
    data, _headers = post(TOKEN_URL, {
        "grant_type": "client_credentials",
        "appkey": appkey, "secretkey": secretkey
    })
    token = data.get("token") if isinstance(data, dict) else None
    if not _success(data) or not isinstance(token, str) or not token:
        raise RuntimeError("Kiwoom OAuth did not return a usable token")
    return token


def _page(token, query, cont="N", next_key="", post=_http_post):
    body = {
        "dt": query,
        "stk_cd": STOCK,
        "amt_qty_tp": "1",  # amount
        "trde_tp": "0",     # net trade
        "unit_tp": "1"      # matters for quantity mode; amount is million KRW
    }
    result, headers = post(DAILY_URL, body, {
        "authorization": "Bearer " + token,
        "api-id": TR_ID,
        "cont-yn": cont,
        "next-key": next_key,
    })
    if not _success(result):
        raise RuntimeError("Kiwoom investor-by-stock endpoint returned failure")
    if not isinstance(result.get("stk_invsr_orgn"), list):
        raise ValueError("Kiwoom investor-by-stock daily rows unavailable")
    return result, {k.lower():v for k,v in headers.items()}


def fetch_investor_history(appkey, secretkey, last_market_date,
                           permitted_dates, post=_http_post, max_pages=6):
    """Fetch up to 6 pages; never silently describe partial history as full."""
    if not last_market_date:
        return [], {"status":"missing_market_date","pages":0,"truncated":False}
    query_date = _date(last_market_date)
    if not query_date:
        raise ValueError("Invalid market date")
    token = get_token(appkey, secretkey, post=post)
    all_rows = {}
    continuation = ("N", "")
    pages = 0
    truncated = False
    while pages < max_pages:
        result, headers = _page(
            token, query_date.replace("-",""),
            cont=continuation[0],
            next_key=continuation[1], post=post)
        pages += 1
        for row in normalize_daily(result,permitted_dates=permitted_dates):
            all_rows[row["date"]] = row
        has_more = (headers.get("cont-yn","N").upper()=="Y")
        key = headers.get("next-key","")
        if not has_more:
            break
        if not key:
            # Provider says more pages, but supplies no cursor.
            truncated = True
            break
        if pages >= max_pages:
            truncated = True
            break
        continuation = ("Y",key)
    rows = [all_rows[k] for k in sorted(all_rows)]
    return rows, {
        "status": ("partial_pagination" if truncated else
                   "ok" if rows else "empty_rows"),
        "pages": pages,"truncated": truncated,
        "rows":len(rows),"asof":rows[-1]["date"] if rows else None,
        "api_id":TR_ID,"unit":"KRW","read_only":True
    }


def collect_if_connected(price_rows, appkey=None, secretkey=None,
                         post=_http_post):
    """Convenience wrapper for GitHub Secrets configuration."""
    appkey=appkey if appkey is not None else os.getenv("KIWOOM_APP_KEY","")
    secretkey=secretkey if secretkey is not None else os.getenv("KIWOOM_SECRET_KEY","")
    if not appkey or not secretkey:
        return [], {"status":"not_configured","pages":0,"truncated":False}
    prices = [p for p in price_rows if p.get("date")]
    return fetch_investor_history(
        appkey,secretkey,
        prices[-1]["date"] if prices else None,
        {p["date"] for p in prices},post=post)
