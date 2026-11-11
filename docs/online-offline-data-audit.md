# Online and offline data audit (2026-11-11)

## Findings verified against the live JSON and source code

- Amazon has 418 saved category-rank observations across nine countries. Latest observations are 2026-11-11. The Top100 snapshot covers twelve country marketplaces, but all have incomplete product-brand identity coverage. Confirmed Medicube counts are lower bounds, not exact total counts or sales. Zero confirmed products is not confirmed absence.
- Google Trends has 12,931 points in sixteen markets, last observation 2026-11-09. Rebuilding the dashboard does not advance that observation date. Values are normalized search interest, not comparable absolute sales or cross-country search volume.
- Ulta's 2026-11-11 catalog observation contains 69 entries, 37 online-only entries, and three exclusives. The subtraction of total minus online-only is not a verified offline assortment or store count. One product's review history has three observations (Nov 9–11), each 211 reviews / 3.9 rating. This is not chain-wide sell-through.
- Target's latest catalog and product-review collection failed. The historical 104k purchase badge was already marked excluded in data but still appeared as a large numeric headline in one panel. The collector's plain-text proximity heuristic cannot prove badge-to-product identity. Numeric display and new heuristic badge collection are disabled pending product-scoped verification.
- Boots' search YoY figure is a dated company-release observation (Nov 2), not an automatically updated sales series. Costco presence is a media-reported event, not POS. Other retailer links do not imply any actual measured observations.
- Retailer cards looked only at the empty manual observations array, despite successful automatic reference observations. They now use the reference and review records, preserve the observation date, and distinguish failed collection from actual sales availability.
- Partial retail collection returned status `ok`. It now returns `partial` or `unavailable` as applicable, retaining old observations unchanged on failure.

## Regional revenue and channel shares

- Official Q2 IR p.7 reports regional sales in KRW millions. Converted to KRW 100m: North America 3762.51, Europe 1450.84, Asia 1211.42, other 617.41, Korea 633.15.
- Official Q3 IR p.6 reports Korea 50244 KRW million and whole-company rounded shares: North America 46%, Europe 23%, Asia 15%, other 10%. Overseas amounts are estimates using total revenue 7731.15 KRW 100m times those rounded shares, not separately reported exact regional sales. Other-region estimate is 773.12, not the prior unsupported residual 735. Rounded-share estimates need not sum to exact company revenue.
- Q2 offline shares quoted in the Aug 5 conference-call report are North America ~20% and Europe ~50%. A separate US ~23% statement has a different denominator and is not combined into a 20–23% North American range. Q3 report gives North America ~30%, Europe ~40%. These are management comments relayed by media, not audited retail POS.
- Regional numbers are now a source-linked, manually checked quarterly snapshot in `reference_signals.json`; they are not falsely presented as an automatic fiscal-data feed. Q3 estimated QoQ is labeled accordingly.

Sources:
- https://apr-in.aprd.io/ir/APR_%EA%B2%BD%EC%98%81%EC%8B%A4%EC%A0%81_2Q26_KOR_vF.pdf#page=7
- https://apr-in.aprd.io/ir/APR_%EA%B2%BD%EC%98%81%EC%8B%A4%EC%A0%81_3Q26_KOR_vFF.pdf#page=6
- https://m.dnews.co.kr/m_home/view.jsp?idxno=202608051331446520886
- https://m.dnews.co.kr/uhtml/view.jsp?idxno=202610301413110070925

## Remaining gaps

No direct offline POS sales, retailer reorder volumes, or complete country Amazon brand identities were obtained. Target access failures are not bypassed. No API credit budget was increased and no collection was forced. More history and validated product identities are needed before inferring trends. The Google Trends source message about missing CSV can coexist with retained API observations; the UI now shows actual observation date rather than suggesting today’s data are fresh.
