"""Apply only verified new ECB reference fixings and derived USD values."""
import copy
import csv
import io
import json
from pathlib import Path

import update_data as market_io

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"
PREFIX = "window.APR_BOOTSTRAP = "
LABEL = "ECB official historical CSV ZIP"
PRICE_FIELDS = {"close_usd", "usdkrw", "eurkrw", "fx_usd_date", "fx_eur_date"}


def refresh_local(data_dir=DATA):
    read = lambda name: json.loads((data_dir / name).read_text(encoding="utf-8"))
    collector, display, status = [read(n) for n in ("data.json", "market.json", "status.json")]
    original = (data_dir/"bootstrap.js").read_text(encoding="utf-8").strip()
    if not original.startswith(PREFIX) or not original.endswith(";"):
        raise RuntimeError("Invalid bootstrap; not modified")
    bootstrap = json.loads(original[len(PREFIX):-1])
    input_fx = market_io.fetch_fx_ecb_zip()
    before = market_io.load_previous(data_dir)
    old = market_io.saved_fx(before)
    sources = {"USD": LABEL + " (EUR/KRW ÷ EUR/USD)", "EUR": LABEL}
    fx, sources, _ = market_io.reconcile_fx(
        old, before["meta"].get("fx_sources") or {}, input_fx, sources)
    for ccy in ("USD", "EUR"):
        if not fx.get(ccy) or max(input_fx.get(ccy, {}), default="") < max(old.get(ccy, {}), default=""):
            raise RuntimeError(f"{ccy} official feed unavailable or behind retained date")
    valid_dates = {max(fx[ccy]) for ccy in fx}
    if len(valid_dates) != 1:
        raise RuntimeError("ECB cross-rate latest dates do not match")
    latest = valid_dates.pop()

    def apply_fx(doc):
        patched = copy.deepcopy(doc)
        aligned = market_io.pack(doc["series"], doc["meta"].get("stock_source"),
                                 fx, sources, [], {}, doc["logistics"])
        for key in ("usd_fx_last", "eur_fx_last", "fx_sources"):
            patched["meta"][key] = aligned["meta"][key]
        patched["fx"] = aligned["fx"]
        patched["series"] = aligned["series"]
        strip = lambda rows: [{k: v for k, v in r.items() if k not in PRICE_FIELDS}
                              for r in rows]
        assert strip(patched["series"]) == strip(doc["series"])
        assert patched["logistics"] == doc["logistics"]
        return patched

    repaired_collector, repaired_display = map(apply_fx, (collector, display))
    status["fx_last"] = latest
    bootstrap.update(market=repaired_display, status=status)
    as_json = json.dumps(repaired_collector, ensure_ascii=False, separators=(",", ":"))
    table = io.StringIO()
    columns = ("date", "open_krw", "high_krw", "low_krw", "close_krw", "close_usd",
               "usdkrw", "eurkrw", "fx_usd_date", "fx_eur_date", "volume")
    writer = csv.DictWriter(table, fieldnames=columns, extrasaction="ignore")
    writer.writeheader()
    writer.writerows(repaired_collector["series"])
    for name, text in (("data.json", as_json), ("data.js", "window.APR_DATA = "+as_json+";\n"),
                       ("history.csv", table.getvalue())):
        market_io.write_atomic(data_dir/name, text)
    for name, value in (("market.json", repaired_display), ("status.json", status)):
        market_io.write_atomic(data_dir/name, json.dumps(value, ensure_ascii=False, indent=2)+"\n")
    market_io.write_atomic(data_dir/"bootstrap.js", PREFIX+
                           json.dumps(bootstrap, ensure_ascii=False, separators=(",", ":"))+";\n")
    print(json.dumps({"status": "verified", "ecb_date": latest, "eurkrw": fx["EUR"][latest],
                      "usdkrw": fx["USD"][latest],
                      "stock_date": repaired_display["meta"].get("stock_last"),
                      "stock_close_krw": repaired_display["series"][-1]["close_krw"],
                      "stock_close_usd": repaired_display["series"][-1]["close_usd"]}))


if __name__ == "__main__":
    refresh_local()
