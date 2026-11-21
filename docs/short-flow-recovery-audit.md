# APR short trading / reported positions / pension recovery audit

Verified 2026-11-11. This is an implementation audit, not a statement that a new live feed is connected.

## Existing paths and the actual blocker

- KRX/pykrx detailed investor amounts and shorting status are attempted in `flows_collect.py`. Empty/changed responses are failures, not observed zeros. A login/permission barrier must not be bypassed with another identity, proxy or copied session.
- Naver fallback has individual/foreign/institution quantities and estimated cash amounts (net shares × closing price). It does not supply pension. This estimate is not actual executed cash value.
- Kiwoom `ka10059` adapter already maps `penfnd_etc` to pension (part of institution), amounts × 1,000,000 KRW. Existing secrets alone are insufficient on a dynamic GitHub-hosted runner. Use an authorized machine with a stable outbound IP registered with Kiwoom, and confirm provider terms before exposing output. Do not enable `KIWOOM_ALLOW_DYNAMIC_IP=1` merely to retry a blocked IP; its existing name is misleading.
- KIS `FHPST04830000` daily short sales supports quantities and amount ratios, but not reported net short positions. Its key pair is optional and no live KIS data was acquired in this audit.
- FSC/KSD lending volume, outstanding lending and repayments cannot replace reported net short positions or short trading.

## Implemented and tested

`kis_short_sales.py` now reads the previously discarded daily **value** ratio. It independently computes `ssts_tr_pbmn / acml_tr_pbmn × 100` when both are valid, and checks against provider rounded `ssts_tr_pbmn_rlim` (0.02 percentage-point tolerance). A conflict keeps the value ratio missing. Without both amounts it can use a valid provider value ratio. It never substitutes volume ratio or cumulative fields. Absolute monetary values remain withheld until the amount unit is independently/live verified. This does not manufacture missing data or restore connectivity.

## Practical next steps needing user cooperation

1. Prefer the already-configured Kiwoom route: choose an authorized always-on machine/static outbound IP, register that IP in Kiwoom, then run only read-only data endpoints. Verify latest APR rows against the provider and confirm distribution rights. No new key should be pasted into chat.
2. Alternative KIS: user needs an eligible KIS account/API application and the pair stored in repository Actions Secrets `KIS_APP_KEY`, `KIS_APP_SECRET`. Investor daily API `FHPTJ04160001` has `fund_ntby_qty` and `fund_ntby_tr_pbmn`; verify quantity/amount units and that "기금" matches intended "연기금 등" before implementing a dashboard label. Market code `J` is KRX; do not silently combine it with NXT or `UN` data. KIS sample lists J/NX/UN, unlike the site's current KRX-only fallback.
3. Reported net short balance: use an authorized KRX export/import while assessing an approved recurring KRX feed. Keep its observation date separate from download time and short-selling trade date. Do not promise a free anonymous API; none was verified in this audit.
4. Public GitHub Pages is not automatically permitted for broker/market data just because an API key works. Check the provider/data-owner's actual distribution license first. A private HTML UI alone is insufficient if raw JSON or Git history remains public.

## Primary references

- KIS daily short sales field mapping: https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/daily_short_sale/chk_daily_short_sale.py
- KIS investor daily endpoint/market codes: https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/investor_trade_by_stock_daily/investor_trade_by_stock_daily.py
- KIS investor fields: https://github.com/koreainvestment/open-trading-api/blob/main/examples_llm/domestic_stock/investor_trade_by_stock_daily/chk_investor_trade_by_stock_daily.py
- KIS provider-information page explicitly discusses third-party service and Koscom information-use contracts: https://apiportal.koreainvestment.com/provider-info (official search-index excerpt read; full-page fetch timed out)
- KRX official explanation of distinction between lending balance and short sale: https://data.krx.co.kr/contents/MDC/STAT/srt/MDCSTAT317.jsp

Tests: `python -m unittest discover -s tests -p 'test_kis_short_sales.py' -v` (9 passed); `python -m unittest discover -s tests -p 'test_flows.py' -q` (17 passed). Offline only; no secrets, no live broker test, no orders, no deployment.

## Follow-up 2026-11-11 (latest main)

- Latest committed `data/flows.json`: Kiwoom credentials configured but host disabled; KIS pair absent; KRX detail/basic zero rows; pension and short observations still absent. Only the Dot cloud computer appears in the connected-environment list. Do not claim successful reconnection.
- Kiwoom's official https://openapi.kiwoom.com/intro/serviceInfo confirms IP allowlisting is required and up to 10 IPs may be registered. Minimum user step: connect the intended PC and confirm/register its egress IP via account App Key management. A newly registered network/security permission needs the user's action-time confirmation. An always-on stable-IP environment is needed for reliable unattended collection.
- https://openapi.krx.co.kr/contents/OPP/INFO/service/OPPINFO004.cmd does not list investor breakdown or net-short-position endpoints. A generic KRX API key is not a verified fix for these metrics.
- KRX OPEN API terms at https://openapi.krx.co.kr/contents/OPP/INFO/OPPINFO002.jsp explicitly contemplate noncommercial result screens with attribution. Do not overstate this as a blanket public-display ban; API terms, marketplace access, and broker redistribution terms differ.
- Public secondary source https://fastjusik.com/pension/s/278470 shows a 2026-11-10 pension summary, but official reconciliation and redistribution rights are unverified. It was not imported as official data. NPSight's accessible indexed APR page is dated May 2026, so it is not an acceptable latest-data substitute.

### Manual official export fallback

Download the APR-only KRX investor daily **net buying value** and short trading / reported net position CSV using authorized access, keeping the selected market, date range and unit. Convert to `imports/apr_investor_daily.csv` or `imports/apr_short_daily.csv`; this is not an automatic generic KRX-export parser. Investor cash fields are KRW (multiply explicitly if the source is million KRW), quantities are shares, ratios are percent (2.35 means 2.35%, not 0.0235). Preserve observation dates and source URL, not the download date. `pension` is a subset of institution, not an extra total.

The short CSV path now accepts decimal `short_value_ratio_pct` and `short_volume_ratio_pct`, which were previously omitted. Imports preserve source_url and reject future dates and explicitly mismatched tickers; missing/invalid ratios do not become zeros. Imported data stays `manual_source_linked_unverified` until a real source comparison is done. No real CSV has been supplied in this follow-up. Unit/cross-source verification and permitted public use remain required before publishing new imported observations.
