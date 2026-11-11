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

## 100/100 target feasibility (2026-11-11)

`identity_coverage_count` has historically meant title OR brand is present. It
must not be read as 100 explicit brand fields. A separate target now requires
100 distinct ASINs at ranks 1..100 and nonblank title AND explicit brand on all
100 rows. Missing title/brand ASINs are recorded for auditable backlogs. No brand
is inferred from the first word of a title. Title-based Medicube matches remain
observations, not a guarantee of complete supplier identity verification.

Saved 2026-11-11 snapshots: 12 markets, 1,200 ranks, 1,000 title-or-brand
identities, 200 unresolved. Cache holds 1,271 titled records but only 32 records
with explicit brand. These cache counts are not the current rank-list counts.
At two unknown-PDP slots/day, 200 fixed missing identities alone take 100 days
if every query succeeds and no new names become missing; future chart cards may
resolve some sooner and chart churn may create more. Thus PR43 is an incremental
coverage optimization, not a complete-collection solution.

Existing 12-market daily frequency, 4 PDP/day and 900-credit monthly cap cannot
guarantee the requested completeness. Do not change limits or enter an unbounded
retry loop. A paid supplier change requires separate approval and a measured
pilot. The provider documentation is not an actual-account response test.

Cost scenarios (USD sticker prices, taxes/retries excluded; no purchases made):
- Scrape.do Hobby: $29/month, 250,000 credits. At observed 1 credit/request,
  24 list requests + up to 480 missing-title PDP requests + 2 known-brand checks
  per day = 15,180 credits/30 days. Revalidating title+brand for all 1,200 entries
  instead would be (24+1200+2)*30=36,780 credits. Both exceed existing local caps.
- Scrapingdog Lite: $40/month; list endpoint costs 5 credits, so 12 lists/day
  for 30 days = 1,800 credits. Example list response omits brand; additional PDP
  cost and actual complete title coverage still need verification. Free trial
  100 credits permits 20 list calls nominally, not ongoing monthly coverage.
- API.SH existing list endpoint example has 30 items and documents 2 pages;
  there is no verified complete-list substitute. Product enrichment costs
  3 credits and shares an existing 750-credit safety budget with Trends.

Primary references:
https://scrape.do/documentation/amazon-scraper-api/bestsellers/
https://scrape.do/pricing/
https://www.scrapingdog.com/documentation/amazon-bestsellers-api/
https://www.scrapingdog.com/amazon-scraper-api/
https://api.sh/docs/amazon-bestsellers

Before any new supplier activation: verify public-data rights and service terms,
validate all 12 marketplaces against the intended Beauty category, count raw
ranks/unique ASINs/titles/explicit brands, preserve response timestamps and cost,
and retain incomplete state on failure. Never bypass a denial or mark missing
rows complete. No production target improvement has yet been measured.

## Scheduled response diagnostics and crawling review

The follow-up to PR43 adds counts from requests the scheduled collector already
makes. It never triggers extra pages, PDPs, retries or a workflow dispatch.
`amazon_collection_diagnostics.json` contains the latest per-market page numbers,
UTC receipt timestamps, fixed validation outcomes and numeric field counts. It
stores no raw JSON/HTML, URLs, titles, headers or credentials. Failed-page
validation is retained even if no snapshot can be built. Diagnostic write
failure does not fail the normal collection. Historic counts are not fabricated.

Access review on 2026-11-11:
- https://www.amazon.com/robots.txt explicitly disallows ChatGPT-User,
  OAI-SearchBot and GPTBot. No user-agent impersonation, proxy, CAPTCHA bypass,
  browser workaround or direct crawling was performed.
- The US Conditions of Use URL returned 503 in the permitted web tool. Indexed
  official Amazon Conditions of Use text excludes product-list collection and
  robots/data-mining from the ordinary access license:
  https://sellercentral.amazon.com/gp/help/external/201824360
- Official UK terms also restrict extraction/reuse without consent:
  https://digprjsurvey.amazon.co.uk/csad/help/node/GLSBYFE9MGKKQXXM
- robots is neither a data license nor a complete legal determination. A paid
  third-party API subscription is not evidence of Amazon permission. Verify
  applicable supplier rights and reuse terms before expansion; do not describe
  unrestricted crawling as legally cleared. EU DSA researcher access is a
  separate qualified-purpose route, not assumed applicable to this dashboard:
  https://trustworthyshopping.aboutamazon.com/digital-services-act-dsa-amazon-eu-store-data-access-for-researchers

The existing GitHub morning run 42921082373 used registered API secrets and
completed collection. Its logs contain aggregate totals, not raw API responses.
The current manual dispatch runs the full collector and other sources, and is
not a bounded two-page diagnostic mode. It was not triggered for this audit.
No new API account, key, spending or direct source call was introduced. The
next authorized regular collection can provide the new non-sensitive evidence;
this change does not claim a live 100-item result in advance.
