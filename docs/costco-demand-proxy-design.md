# Costco indirect demand panel — proposal

Reviewed 2026-11-11. This is a design and source-access assessment, not a live collector or sales estimate.

## Recommended starting product

Medicube Zero Pore Exfoliating Toner Pads with Refill, 200-count, Costco US item 2091779:
https://www.costco.com/p/-/medicube-zero-pore-exfoliating-toner-pads-with-refill-200-count/4201051963

The item number and 200-pad pack are confirmed on Costco's product page. Keep this distinct from Ulta/Target packs: compare per-pad price only when an actual price and pack size are verified. The present unauthenticated view does not yield a verified review aggregate or normal Costco.com price. A standalone “0” beside a compare widget is not a review count. A no-location “Unavailable” message is not evidence of US-wide stockout.

Same-Day has a corresponding item page:
https://sameday.costco.com/store/costco/products/137374909-medicube-zero-pore-pads-refill-pack-200-ct

It displays a price and out-of-stock message, but without a validated delivery location these cannot serve as a warehouse-level stock observation. Same-Day/Instacart price is a different channel from warehouse and Costco.com; never splice the price series.

## Panel structure

1. **Assortment and distribution:** newly confirmed SKU/pack listings and officially announced warehouse expansion, with date and source type. A catalog listing alone does not verify offline distribution or sell-through.
2. **Fixed-warehouse availability:** at a stable panel of, for example, 12–20 warehouses across four US regions, record `in_stock`, `limited_stock`, `out_of_stock`, `not_carried`, or `unknown`, plus item number, warehouse ID, timestamp, evidence and promotion status. Do not merge `not_carried`, failed lookup, and out-of-stock. Start only after a permitted source is available; the number of stores is a suggested research sample, not measured current coverage.
3. **Replenishment-like transitions:** report confirmed out-of-stock → in-stock transitions and observed intervals for the same item/store. Call them inventory-display changes, not retailer purchase orders or shipment units. Two consecutive checks can improve confidence; exact transition time is interval-censored. Previously unobserved stores are not necessarily new distribution.
4. **Review activity:** track verified same-item review count, rating, 7/28-day count change, and acquisition source. Negative count changes may be moderation or merged variants, not negative sales. Reviews may combine online and in-store purchasers; never convert them directly to units.
5. **Price and promotion:** regular/promotional price, currency, pack size, per-pad price, promotion window. Separate normal-price and promotional observation windows. Falling prices are not automatically demand weakness or clearance.

## Interpretation

Do not publish a numerical sales-growth estimate or weighted “demand score” before calibrating against independent actuals. Show separate cards with evidence quality and sample coverage.

- More carried stores and increasing reviews: evidence of broader reach and consumer engagement, not quantified sales.
- Repeated stockout/reappearance at fixed stores plus faster reviews without a deep discount: stronger qualitative demand signal, still confounded by stock allocation and logistics.
- Persistent missing item/stockout without review growth: ambiguous; investigate distribution cuts, supply delays, seasonality and regional availability.
- Review activity rises only during discount periods: promotion-linked response, not proof of sustained full-price demand.

Suggested availability formula is `verified in-stock stores / stores with a verified current availability state`, with denominator and unknown count visible. Fixed-panel comparisons must use the same stores/items across dates. No “national stockout percentage” from an unrepresentative sample.

## Access and implementation gates

Costco's terms (updated Oct 7, 2026), section 9, restrict robotic/agent extraction and applications interacting with the service without prior written consent:
https://www.costco.com/f/-/terms-and-conditions-of-use

Do not build or deploy a direct unattended scraper. A compliant first version can store source-linked company announcements and process user-supplied/authorized observation exports or photographs. Any third-party feed must establish legitimate data access and redistribution rights, APR item coverage, store-level provenance, update frequency, and cost before adoption. A vendor calling itself an API is not proof of authorization. Do not subscribe or contact Costco/vendors without permission.

Official warehouse guidance says availability features apply only where enabled and online inventory is not a duplicate of warehouse inventory:
https://customerservice.costco.com/app/answers/detail/a_id/11031

Official app/customer-service lookup guidance says inventory and price may lag up to 30 minutes and unavailable items can disappear. Its customer-service flow requires identity/login/location; no such information was provided and no login/contact was attempted:
https://customerservice.costco.com/app/answers/answer_view/a_id/1015066/~/how-do-i-check-warehouse-inventory-and-prices%253F

Online disappearance is ambiguous between unavailable-online and out-of-stock:
https://customerservice.costco.com/app/answers/detail/a_id/669

## Initial display today

- Product identity: confirmed, item 2091779 / 200 pads.
- Warehouse observation coverage: 0 verified stores; not configured.
- Reviews/rating: unverified, not zero.
- Price: no standardized warehouse baseline; Same-Day excluded from warehouse comparisons.
- Demand direction: insufficient observations, not “weak.”
- Direct automated collection: not enabled; permission/data-source gate outstanding.
