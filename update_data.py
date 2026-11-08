#!/usr/bin/env python3
"""APR 278470 price/FX updater — Python standard library only.

Sources:
 - Naver Finance public fchart XML, fallback Naver siseJson, fallback Yahoo Finance chart
 - ECB official historical EUR reference rates (USD/KRW derived), fallback Frankfurter v2/v1

No values are synthesized or interpolated. On non-FX-business stock days, preceding FX fix
may be used and its actual date is preserved. Outputs JSON, JS-for-file-preview, and CSV.
"""
import argparse
import bisect
import csv
import io
import zipfile
import datetime as dt
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import time
from urllib import request, parse, error
import xml.etree.ElementTree as ET
from html.parser import HTMLParser
from freight_official import fetch_latest as fetch_customs_official_latest

START = dt.date(2025, 6, 1) # FX reference history for valuation charts from Jun 2025
HISTORY_START = dt.date(2025, 6, 1)  # 기술적 지표 MA200 워밍업, 화면은 2026-05부터
BASE = Path(__file__).resolve().parent
UA = "Mozilla/5.0 (compatible; APRMarketMonitor/1.0; personal dashboard)"


def get_bytes(url, timeout=20, extra_headers=None):
    headers = {"User-Agent": UA, "Accept": "application/json,text/xml,*/*"}
    if extra_headers:
        headers.update(extra_headers)
    req = request.Request(url, headers=headers)
    with request.urlopen(req, timeout=timeout) as res:
        return res.read()


def iso_today_kr():
    try:
        from zoneinfo import ZoneInfo
        return dt.datetime.now(ZoneInfo("Asia/Seoul"))
    except Exception:
        return dt.datetime.utcnow() + dt.timedelta(hours=9)


def normalize_rows(entries):
    result = {}
    today = iso_today_kr().date()
    for obj in entries:
        try:
            date = dt.date.fromisoformat(str(obj["date"]))
            price = float(obj["close_krw"])
            if date < HISTORY_START or date > today or price <= 1000 or price >= 10000000:
                continue
            item={"date":date.isoformat(),"close_krw":int(round(price)),"volume":int(obj.get("volume") or 0)}
            for name in ("open_krw", "high_krw", "low_krw"):
                v=obj.get(name)
                if v is not None and float(v)>0: item[name]=int(round(float(v)))
            if item.get("high_krw") is not None and item.get("low_krw") is not None:
                if item["low_krw"]>item["high_krw"] or not item["low_krw"]<=item["close_krw"]<=item["high_krw"]:
                    continue
            result[date.isoformat()] = item
        except Exception:
            continue
    # Reject intraday incomplete candle, if on weekday before official market close+buffer
    now = iso_today_kr()
    if now.hour < 15 or (now.hour == 15 and now.minute < 45):
        result.pop(now.date().isoformat(), None)
    return [result[k] for k in sorted(result)]


def fetch_stock_naver_xml():
    q = parse.urlencode({"symbol": "278470", "timeframe": "day", "count": 500, "requestType": 0})
    raw = get_bytes("https://fchart.stock.naver.com/sise.nhn?"+q, extra_headers={"Referer":"https://finance.naver.com/"})
    # Naver publishes EUC-KR XML. ElementTree's byte parser does not support this
    # multi-byte encoding in some Python builds, so decode first.
    root = ET.fromstring(raw.decode("euc-kr", errors="replace"))
    out = []
    for item in root.iter("item"):
        p = (item.attrib.get("data") or "").split("|")
        if len(p) < 6 or not re.fullmatch(r"\d{8}",p[0]):
            continue
        out.append({"date":f"{p[0][:4]}-{p[0][4:6]}-{p[0][6:8]}", "open_krw":p[1], "high_krw":p[2], "low_krw":p[3], "close_krw":p[4], "volume":p[5]})
    return normalize_rows(out)


def fetch_stock_naver_js():
    q = parse.urlencode({"symbol": "278470", "requestType":1,"startTime":"20250601","endTime":iso_today_kr().strftime("%Y%m%d"),"timeframe":"day"})
    raw = get_bytes("https://api.finance.naver.com/siseJson.naver?"+q, extra_headers={"Referer":"https://finance.naver.com/"}).decode("utf-8-sig",errors="replace")
    # Returned as JS-like arrays with a header row and optional trailing commas.
    chunks = re.findall(r"\[\s*(20\d{6})\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)\s*,\s*([0-9.]+)",raw)
    out = []
    for row in chunks:
        d=row[0]
        out.append({"date": f"{d[:4]}-{d[4:6]}-{d[6:]}","open_krw":row[1],"high_krw":row[2],"low_krw":row[3],"close_krw":row[4],"volume":row[5]})
    return normalize_rows(out)


def fetch_stock_yahoo():
    first=int(time.mktime(dt.datetime(2025,6,1,0,0).timetuple()))
    last=int(time.time())+86400
    q=parse.urlencode({"period1":first,"period2":last,"interval":"1d"})
    urls=["https://query1.finance.yahoo.com/v8/finance/chart/278470.KS?"+q, "https://query2.finance.yahoo.com/v8/finance/chart/278470.KS?"+q]
    last_error=None
    for url in urls:
        try:
            o=json.loads(get_bytes(url).decode("utf-8"))["chart"]["result"][0]
            quotes=o["indicators"]["quote"][0]
            tz=o.get("meta",{}).get("exchangeTimezoneName","Asia/Seoul")
            out=[]
            for stamp,close,volume in zip(o.get("timestamp",[]),quotes.get("close",[]),quotes.get("volume",[])):
                if close is None:continue
                # Exchange timestamps are daily session dates; render in KST.
                d=dt.datetime.fromtimestamp(stamp,dt.timezone(dt.timedelta(hours=9))).date().isoformat()
                idx=len(out)
                # Use same index as the input timestamp: some rows have null close and are skipped.
                pos=o.get("timestamp",[]).index(stamp)
                hi=quotes.get("high",[]); lo=quotes.get("low",[]); op=quotes.get("open",[])
                out.append({"date":d,"close_krw":close,"volume":volume or 0,
                            "high_krw":hi[pos] if pos<len(hi) else None,
                            "low_krw":lo[pos] if pos<len(lo) else None,
                            "open_krw":op[pos] if pos<len(op) else None})
            return normalize_rows(out)
        except Exception as ex:
            last_error=ex
    raise RuntimeError(f"Yahoo chart returned no data: {last_error}")


def fetch_stock():
    attempts=[("네이버 금융 (일별 종가)",fetch_stock_naver_xml), ("네이버 금융 (기간별 종가)",fetch_stock_naver_js), ("Yahoo Finance (종가)",fetch_stock_yahoo)]
    errors=[]
    for name,fn in attempts:
        try:
            rows=fn()
            # Require meaningful coverage from May, not just latest quotes
            if len(rows) < 30 or rows[0]["date"] > "2026-05-22":
                raise RuntimeError(f"insufficient history: {len(rows)} observations, earliest {rows[0]['date'] if rows else 'none'}")
            return rows,name,errors
        except Exception as ex:
            errors.append(f"{name}: {str(ex)[:160]}")
    return [],None,errors


def parse_ecb_reference_csv(raw):
    """Convert ECB EUR-based daily reference fixings into KRW/EUR and KRW/USD.

    Each row is the same ECB fixing date. For example if 1 EUR = 1500 KRW
    and 1 EUR = 1.2 USD then 1 USD = 1250 KRW. Historical ECB reference
    rates are not Korean onshore transaction rates.
    """
    reader=csv.DictReader(io.StringIO(raw.decode("utf-8-sig",errors="replace")))
    fields={k.strip().upper():k for k in (reader.fieldnames or []) if k}
    if not {"DATE","USD","KRW"}.issubset(fields):
        raise ValueError("ECB daily CSV missing Date, USD or KRW")
    out={"USD":{},"EUR":{}}
    today=iso_today_kr().date()
    for row in reader:
        try:
            date=dt.date.fromisoformat((row[fields["DATE"]] or "").strip())
            if not START <= date <= today:continue
            usd_per_eur=float((row[fields["USD"]] or "").strip())
            krw_per_eur=float((row[fields["KRW"]] or "").strip())
            if not (0.1 < usd_per_eur < 5 and 100 < krw_per_eur < 10000):continue
            d=date.isoformat()
            out["USD"][d]=round(krw_per_eur/usd_per_eur,6)
            out["EUR"][d]=krw_per_eur
        except (ValueError,TypeError,KeyError):
            continue
    if len(out["USD"]) < 30 or min(out["USD"]) > "2026-05-22":
        raise ValueError("ECB reference history insufficient")
    return out


def fetch_fx_ecb_zip():
    """Free ECB full-history CSV ZIP; one request for both required currencies."""
    url="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.zip"
    raw=get_bytes(url,timeout=20,extra_headers={"Accept":"application/zip,application/octet-stream,*/*"})
    with zipfile.ZipFile(io.BytesIO(raw)) as z:
        names=[n for n in z.namelist() if n.lower().endswith(".csv")]
        if not names:raise ValueError("ECB ZIP missing CSV")
        return parse_ecb_reference_csv(z.read(names[0]))


def fetch_fx_ecb_csv():
    url="https://www.ecb.europa.eu/stats/eurofxref/eurofxref-hist.csv"
    return parse_ecb_reference_csv(get_bytes(url,timeout=20,extra_headers={"Accept":"text/csv,*/*"}))


def fetch_fx_v2(base):
    q=parse.urlencode({"from":START.isoformat(),"base":base,"quotes":"KRW"})
    vals=json.loads(get_bytes("https://api.frankfurter.dev/v2/rates?"+q,timeout=25).decode("utf-8"))
    out={}
    for obj in vals:
        if obj.get("base","").upper()==base and obj.get("quote","").upper()=="KRW":
            v=float(obj["rate"])
            if 100 < v < 10000: out[obj["date"]]=v
    return out


def fetch_fx_v1(base):
    q=parse.urlencode({"from":START.isoformat(),"to":"KRW"})
    # legacy supports YYYY-MM-DD.. date range
    url=f"https://api.frankfurter.app/{START.isoformat()}..?"+parse.urlencode({"from":base,"to":"KRW"})
    vals=json.loads(get_bytes(url,timeout=25).decode("utf-8"))
    out={}
    for date,obj in vals.get("rates",{}).items():
        v=obj.get("KRW")
        if v and 100 < float(v) < 10000: out[date]=float(v)
    return out


def fetch_fx():
    out={}; errors=[]; sources={}
    # Preferred: a single official ECB publication includes matching EUR/USD
    # and EUR/KRW dates so the cross-rate is computed without merging fixes.
    for name,fn in (("ECB official historical CSV ZIP",fetch_fx_ecb_zip),
                    ("ECB official historical CSV",fetch_fx_ecb_csv)):
        try:
            both=fn()
            if len(both["USD"])<30 or len(both["EUR"])<30:
                raise RuntimeError("ECB history insufficient")
            return both,{"USD":name+" (EUR/KRW ÷ EUR/USD)","EUR":name},errors
        except Exception as ex:
            errors.append(f"{name}: {str(ex)[:160]}")
    for base in ("USD","EUR"):
        for name,fn in (("Frankfurter v2 (중앙은행 참조환율)",fetch_fx_v2),
                        ("Frankfurter v1 (중앙은행 참조환율)",fetch_fx_v1)):
            try:
                values=fn(base)
                if len(values)<30 or min(values)>"2026-05-22": raise RuntimeError("history insufficient")
                out[base]=values; sources[base]=name
                break
            except Exception as ex:
                errors.append(f"{base} {name}: {str(ex)[:160]}")
    return out,sources,errors

class _TableRows(HTMLParser):
    def __init__(self):
        super().__init__();self.rows=[];self.row=None;self.cell=None
    def handle_starttag(self,tag,attrs):
        if tag.lower()=="tr":self.row=[]
        if tag.lower() in ("td","th") and self.row is not None:self.cell=[]
    def handle_data(self,data):
        if self.cell is not None:self.cell.append(data)
    def handle_endtag(self,tag):
        if tag.lower() in ("td","th") and self.cell is not None and self.row is not None:
            self.row.append("".join(self.cell).strip());self.cell=None
        if tag.lower()=="tr" and self.row is not None:
            self.rows.append(self.row);self.row=None


def fetch_sea_nlic():
    """Public Customs/NLIC monthly indicative freight cost, NOT KITA rates or APR invoice rates."""
    url="https://nlic.go.kr/nlic/seaDmstcOcn.action"
    html=get_bytes(url,timeout=14).decode("utf-8",errors="replace")
    h=_TableRows();h.feed(html)
    out=[]
    for row in h.rows:
        date=next((x for x in row if re.fullmatch(r"2026-(0[5-9]|1[0-2])",x)),None)
        if not date:continue
        ix=row.index(date)
        v=[]
        for x in row[ix+1:]:
            x=x.replace(",","").replace(" ","")
            if re.fullmatch(r"\d+(?:\.\d+)?",x):v.append(float(x))
            if len(v)>=3:break
        if len(v)==3 and all(300<n<30000 for n in v):
            out.append({"month":date,"us_west":v[0],"us_east":v[1],"eu":v[2]})
    out=sorted({x["month"]:x for x in out}.values(),key=lambda x:x["month"])
    if len(out)<5 or out[0]["month"]>"2026-05":raise ValueError("NLIC tables not accessible or changed")
    return out


def pack(stock,stock_source,fx,fx_sources,errors,previous,logistics):
    available=sorted(set(fx.get("USD",{}))|set(fx.get("EUR",{})))
    fx_daily=[]
    for date in available:
        fx_daily.append({"date":date,"usdkrw":fx.get("USD",{}).get(date),"eurkrw":fx.get("EUR",{}).get(date)})
    usd_dates=sorted(fx.get("USD",{}))
    eur_dates=sorted(fx.get("EUR",{}))
    series=[]
    for row in stock:
        d=row["date"]
        j=bisect.bisect_right(usd_dates,d)-1
        k=bisect.bisect_right(eur_dates,d)-1
        usd_date=usd_dates[j] if j>=0 else None
        eur_date=eur_dates[k] if k>=0 else None
        # Do not use stale FX for long outages. Stock date and FX value days differ normally by ≤2.
        if usd_date and (dt.date.fromisoformat(d)-dt.date.fromisoformat(usd_date)).days > 5: usd_date=None
        if eur_date and (dt.date.fromisoformat(d)-dt.date.fromisoformat(eur_date)).days > 5: eur_date=None
        rate=fx["USD"].get(usd_date) if usd_date else None
        eur=fx["EUR"].get(eur_date) if eur_date else None
        series.append({**row,"usdkrw":rate,"eurkrw":eur,"fx_usd_date":usd_date,"fx_eur_date":eur_date,
                       "close_usd":round(row["close_krw"]/rate,4) if rate else None})
    meta={"name":"에이피알","ticker":"278470","market":"KRX","start":START.isoformat(),
          "stock_source":stock_source,"fx_sources":fx_sources,
          "stock_last":stock[-1]["date"] if stock else None,
          "usd_fx_last":usd_dates[-1] if usd_dates else None,
          "eur_fx_last":eur_dates[-1] if eur_dates else None,
          "generated_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
          "coverage_start":stock[0]["date"] if stock else None,
          "complete":bool(stock and stock[0]["date"]<="2026-05-15" and len(stock)>=80 and len(usd_dates)>=80 and len(eur_dates)>=80),
          "errors":errors[:12],
          "logistics_source":logistics.get('source') or '관세청 해상수출 평균 운송비용 통계',
          "note":"주가는 수정주가 또는 공급사 종가. USD 환산=원화 종가/당일 또는 직전 최신 USD/KRW 환율. FX는 중앙은행 참고 환율(서울외국환중개 매매기준율과 다를 수 있음)."}
    return {"meta":meta,"series":series,"fx":fx_daily,"logistics":logistics}


def write_atomic(path, data):
    path.parent.mkdir(parents=True,exist_ok=True)
    fd,p=tempfile.mkstemp(prefix=".apr_",dir=str(path.parent))
    try:
        with os.fdopen(fd,"w",encoding="utf-8",newline="") as f:
            f.write(data)
        os.replace(p,path)
    finally:
        if os.path.exists(p):os.unlink(p)


def save(data,out_dir):
    out_dir.mkdir(parents=True,exist_ok=True)
    as_json=json.dumps(data,ensure_ascii=False,separators=(",",":"))
    write_atomic(out_dir/"data.json",as_json)
    write_atomic(out_dir/"data.js","window.APR_DATA = "+as_json+";\n")
    import io
    sb=io.StringIO()
    fields=["date","open_krw","high_krw","low_krw","close_krw","close_usd","usdkrw","eurkrw","fx_usd_date","fx_eur_date","volume"]
    w=csv.DictWriter(sb,fieldnames=fields,extrasaction="ignore")
    w.writeheader()
    for row in data["series"]: w.writerow(row)
    write_atomic(out_dir/"history.csv",sb.getvalue())
    sb=io.StringIO()
    w=csv.DictWriter(sb,fieldnames=["month","us_west","us_east","eu"])
    w.writeheader()
    for row in data.get("logistics",{}).get("sea",[]):w.writerow(row)
    write_atomic(out_dir/"sea_history.csv",sb.getvalue())


def update(out_dir=BASE/"data", allow_partial=True, refresh_fx=True, refresh_freight=True):
    try:
        previous=json.loads((out_dir/"data.json").read_text(encoding="utf-8"))
    except Exception: previous={}
    stock,source,se=fetch_stock()
    # Afternoon close update intentionally reuses the morning reference FX,
    # avoiding redundant ECB/Frankfurter calls. It does not forecast FX.
    if refresh_fx:
        fx,sources,fe=fetch_fx()
    else:
        fx={'USD':{r['date']:r['usdkrw'] for r in previous.get('fx',[])
                   if r.get('usdkrw') is not None},
            'EUR':{r['date']:r['eurkrw'] for r in previous.get('fx',[])
                   if r.get('eurkrw') is not None}}
        sources=previous.get('meta',{}).get('fx_sources',{})
        fe=[]
    errors=se+fe
    # Public chart endpoints may lag. Never roll back a newer saved daily bar.
    prior=(previous.get('series') or [])
    if stock and prior and stock[-1].get('date','') < prior[-1].get('date',''):
        errors.append('주가 제공처가 저장된 최신 일봉보다 오래됨: 기존 기록 유지')
        stock=[{k:r[k] for k in ('date','open_krw','high_krw','low_krw',
                                'close_krw','volume') if k in r} for r in prior]
        source=previous.get('meta',{}).get('stock_source')
    if not stock and previous.get("series"):
        stock=[{k:r[k] for k in ("date","open_krw","high_krw","low_krw","close_krw","volume") if k in r} for r in previous["series"]]
        source=previous.get("meta",{}).get("stock_source")
        errors.append("주가 갱신 실패: 마지막 정상 기록 유지")
    if not fx and previous.get("fx"):
        fx={"USD":{r["date"]:r["usdkrw"] for r in previous["fx"] if r.get("usdkrw")},
            "EUR":{r["date"]:r["eurkrw"] for r in previous["fx"] if r.get("eurkrw")}}
        sources=previous.get("meta",{}).get("fx_sources",{})
        errors.append("환율 갱신 실패: 마지막 정상 기록 유지")
    elif previous.get("fx"):
        for base,field in (("USD","usdkrw"),("EUR","eurkrw")):
            if base not in fx:
                fx[base]={r["date"]:r[field] for r in previous["fx"] if r.get(field)}
                sources[base]=previous.get("meta",{}).get("fx_sources",{}).get(base,"이전 수집")
                errors.append(f"{base} 환율 갱신 실패: 마지막 기록 유지")
    if not stock:
        raise RuntimeError("주가 정보를 어디에서도 가져오지 못했습니다. " + "; ".join(errors[:3]))
    logistics=previous.get("logistics",{"sea":[],"air":[],"unit":"천원/2TEU"})
    if refresh_freight:
        freight_errors=[]
        updated=False
        # Prefer primary Customs press releases (monthly Customs declaration costs).
        # Keep confirmed historical months and only overwrite a month when it is
        # independently observed. A newer unpublished month is NEVER guessed.
        try:
            official_row,official_url=fetch_customs_official_latest(
                get_bytes,today=iso_today_kr().date())
            existing={x['month']:x for x in logistics.get('sea',[]) if x.get('month')}
            last=max(existing) if existing else ''
            if official_row['month']>=last:
                existing[official_row['month']]=official_row
                logistics={**logistics,"sea":[existing[m] for m in sorted(existing)],
                           "air":logistics.get("air",[]),
                           "unit":"천원/2TEU",
                           "source":"관세청 공식 보도자료 · 해상수출 평균 운송비용",
                           "source_url":official_url,
                           "last_verified_month":official_row['month'],
                           "last_verified_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
                updated=True
        except Exception as ex:
            freight_errors.append("관세청 보도자료: "+str(ex)[:130])
        if not updated:
            try:
                sea=fetch_sea_nlic()
                existing={x['month']:x for x in logistics.get('sea',[]) if x.get('month')}
                for item in sea:existing[item['month']]=item
                logistics={**logistics,"sea":[existing[m] for m in sorted(existing)],
                           "unit":"천원/2TEU",
                           "source":"국가물류통합정보센터 · 해상수출 운송비용",
                           "source_url":"https://nlic.go.kr/nlic/seaDmstcOcn.action",
                           "last_verified_month":sea[-1]['month'],
                           "last_verified_at_utc":dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")}
                updated=True
            except Exception as ex:
                freight_errors.append("NLIC: "+str(ex)[:130])
        if not updated:
            # Preserve last verified observations; make unsuccessful checks visible.
            logistics={**logistics,"last_fetch_failed":True}
            errors.append("해상수출 운송비용 갱신 실패: "+" / ".join(freight_errors[:2])+
                          " (이전 관측치 유지)")
        else:
            logistics["last_fetch_failed"]=False
    # Otherwise preserve monthly Customs/NLIC rows without contacting those sources.
    data=pack(stock,source,fx,sources,errors,previous,logistics)
    save(data,out_dir)
    print(json.dumps({"status":"ok","stock_rows":len(stock),"fx_rows":len(data["fx"]),"complete":data["meta"]["complete"],"stock_last":data["meta"]["stock_last"],"fx_last":data["meta"]["usd_fx_last"],"errors":errors},ensure_ascii=False))
    return data


if __name__=="__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("--out",default=str(BASE/"data"))
    args=parser.parse_args()
    try: update(Path(args.out))
    except Exception as ex:
        print("ERROR:",ex,file=sys.stderr)
        sys.exit(2)
