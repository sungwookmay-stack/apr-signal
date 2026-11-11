# Amazon ranking audit — 2026-11-11

## Verified findings

Public data and repository at audit time both report demand updated_at 2026-11-10T23:10:24Z. `demand.json` contains 418 Amazon observations (416 list positions and two legacy rows), **zero** `verified_product_rank` records. Separately `scrapedo_pdp.json` contains 52 category-specific PDP observations. The date regular expression in build_data.py uses double-escaped digits, rejecting all valid dates. Fixing it restores saved observations without extra provider calls. This establishes a data pipeline defect, not proof that each upstream rank is correct.

All twelve latest market snapshots are dated 2026-11-11 and cover ranks 1–100, but identity coverage is incomplete: US 74, GB 77, DE 81, FR 85, IT 77, ES 80, CA 83, JP 85, AE 89, SA 92, EG 90, BR 87. Counts are observed minima, not total brand presence. US has four confirmed ASINs and 26 unidentified products; a count increase can result from better identification rather than improved sales.

API.SH's fallback previously computed entry/exit when two snapshots had the same rank coverage and same *number* of identified products. Those products need not be identical, so missing identity could falsely imply an exit. Now entry/exit requires both observations to be complete, matching the Scrape.do path.

## Independent page comparison and limits

- Amazon Beauty Best Sellers: https://www.amazon.com/Best-Sellers-Beauty-Personal-Care/zgbs/beauty returned HTTP 503 during the audit. No bypass attempted.
- https://www.amazon.com/dp/B09V7Z4TJG was available through a web-search cached document marked crawled three weeks ago. It verifies Medicube/APR identity and category-specific BSR structure, **not today's rank**. Its cached #1 must not replace the site's 11/11 list position #6.
- Official explanation: https://sell.amazon.com/blog/amazon-best-sellers-rank . BSR reflects sales performance within a category, differs across marketplaces/categories, and is not search ranking or a sales-unit count. Reviews are not direct BSR inputs.

## Recommended next improvements

1. Keep Beauty-list positions and product-page BSR in separate series, with marketplace + ASIN + category + source as keys. Never splice subcategory ranks into a parent-category series.
2. Display identity coverage alongside rank coverage and confirmed count; never call an incomplete zero an absence. Do not use minimum-count growth alone as a sales signal.
3. Add acquisition UTC timestamp, provider snapshot timestamp when supplied, category node, provider identity, and a reproducible response hash. Current date-only records cannot resolve within-day movements.
4. Cache product identities with age and source, refresh stale identities within the existing quota, and favor a fixed panel of core products. Retain gaps rather than forward-fill unobserved ranks.
5. Existing 900-credit local ceiling can cover 28 calls/day at verified one-credit pricing (840/30 days), but absent cost headers reserve three credits and exhaust sooner. Show quota and collection gaps; do not raise paid limits without authorization.
6. Any new provider or redistribution path needs its permitted use checked. Do not bypass Amazon restrictions or treat an API response as official Amazon certification.

## Validation

188 Python tests and all existing Node smoke tests pass. Added integration test proves saved valid PDP rows reach demand.json, invalid dates are excluded, repeated builds do not duplicate records, and no network is used. Added test prevents false entry/exit from equally sized partial snapshots. Actual browser rendering was not tested here. No deployment has occurred as part of this audit.

Code-only deployment also merges saved PDP observations through a pure offline helper, preserving original collection timestamps and synchronizing demand/bootstrap. It does not call collect_demand, API.SH, Scrape.do or Amazon.

## Identity enrichment follow-up

The unchanged daily budget is 2 Best Sellers pages per configured market and
at most 4 PDP calls, under the same monthly fail-closed credit ceiling. PDP
selection reserves 2 slots for confirmed Medicube BSR and 2 for unresolved
identities; spare slots use the other pool. Market round-robin and oldest-check
priority remain. Strategy upgrades do not trigger additional same-day PDP calls.
Stored checks also bound resumed runs to the daily allowance (a process crash
before saving checks remains subject to the pre-existing quota reservation).

New snapshots record observed ranking/card counts, absent cards, empty card
identities, cache fills, rejected ranking rows, and unresolved identities after
PDP enrichment. These are page-row counts, not a provider-throttling diagnosis.
Legacy snapshots are not backfilled with inferred response diagnostics. Cache
identity is not claimed to be freshly verified. An invalid response is marked
invalid/unavailable without inventing the provider's error reason.

Offline fixture: 11 markets with 60 card identities each, 4 PDP calls total:
2 confirmed-brand calls remain, while 2 unknown ASINs gain fixture identities
(previous allocation allowed 1). This is a synthetic allocation regression,
not measured production uplift. No live API request or extra subscription was
made for this change. Next scheduled collection must establish real coverage.
