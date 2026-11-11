# APR Amazon Beauty Top50

## Schedule and scope

Existing daily 07:30 KST scheduled site build; Decodo only on Monday, Wednesday, Friday, Saturday and Sunday. No requests on pushes, manual dispatches, reruns, afternoon/evening refreshes or days outside that selection. GitHub may delay scheduled starts. A run after noon KST is skipped.

Twelve independent Amazon stores: US, GB, DE, FR, IT, ES, CA, JP, AE, SA, EG, BR. No separate collection for QA, KW, AR or CL.

## Data integrity

Each accepted response must contain exactly positions 1–50, 50 unique valid ASINs, 50 nonempty product titles, page1, the expected country domain and Beauty category. Failed countries retain the previous complete observation and expose their latest check status. Historical Top100 is not converted into Top50. No tracking outside Top50.

Official APR brand source (checked 2026-11-11): https://www.apr-in.com/en/apr_about.html

MEDICUBE, APRILSKIN, FORMENT, GLAM.D Bio, NDY and PHOTOGRAY are separated. Exact brand-title matches are **candidates**, not verified brand identity. Multi-brand titles are withheld from single-brand counts. Generic English “nerdy” and short “NDY” alone are intentionally not matched. No brand is inferred solely from a product name such as Booster or PDRN. Brand verified counts require reviewed country-specific ASIN evidence and currently have no automatic promotion.

Movements compare identical ASINs and complete same-country/category snapshots. An absent product is “not in this Top50,” never rank51 or a sales estimate. A first observation is not called a new entry. First live production results remain pending; US, GB and AE were validated in earlier page1 tests, other markets must pass the same checks.

## Request limits and credentials

Entire daily batch is reserved in the repository before network calls. If durable reservation fails, no request occurs. Interrupted unused reservations are conservatively consumed. No retries, maximum 300 reserved requests per month, one request per country per selected date. HTTP errors pause the remaining batch. A local reservation is not provider billing or a dollar cap.

12 markets × 20–23 collection days gives 240–276 requests/month. Previously quoted ~$0.001/request is an estimate, not a verified invoice. No top-up or plan change is performed.

Google Trends retains APISH_KEY. Legacy Amazon API.SH/Scrape.do/PDP production call paths and the old manual smoke workflow are retired. Existing secret values are not exposed or revoked by this change. DECODO_API_KEY remains in Actions secrets.

## Usage conditions

The site owner authorized the limited public summary without a supplier inquiry. This is not a representation that Decodo grants rights to third-party content; applicable terms remain relevant. No denial, CAPTCHA, login or technical access restriction is bypassed.

## Verification

Python collector tests plus JavaScript offline smoke cover gates, completeness, candidate/brand separation, rank changes, partial failure, quota, and no-data rendering. Existing financial, sensitivity, regional and provenance smoke checks remain enabled.
