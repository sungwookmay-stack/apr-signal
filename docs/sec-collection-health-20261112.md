# SEC collection health verification

- Official submissions and EFTS both responded successfully in the inspection environment.
- Full collector verified at `2026-11-11T16:46:40+00:00`: three previously reviewed KBTY filings retained, zero newly series-verified filings. Last verified filing remains 2026-10-28. This does not establish ETF trading or APR holdings.
- Prior stored `HTTPError` lacked HTTP status, so its precise original cause cannot be established. Current success does not guarantee GitHub Actions network success.
- Removed the duplicated SEC workflow step (same condition, same collector).
- Added safe endpoint/error-type/HTTP-status diagnostics, and separate last-attempt / last-success display. No URLs, response bodies, credentials, impersonation, proxy bypass or extra paid service.
- 403 and 429 are retained as failures, not success; no immediate same-endpoint retries. Existing official submissions → EFTS fallback remains.
- Python suite: 224 tests passed. SEC UI tests cover current successful observation and unsuccessful/no-success states. No Amazon/Trends APIs invoked by this work.

## Correction: November 10 CERT omission

The earlier zero-new count was incorrect as a completeness claim: CERT was excluded from both candidate filters. Additionally, the CERT index header has no SERIES-ID, so simply adding its form would still omit it. The November 10 NYSE Arca certification (0001143362-26-000444) was read directly from the official PDF and added to the reviewed registry. It confirms listing/registration approval, not first trade or APR holdings.

CERT now has a separate identity check: matching trust CIK header plus exact fund name, exchange and listing/registration approval in the official PDF (pypdf). Neither filename nor CIK alone suffices. An unreadable/unmatched CERT is explicitly pending/incomplete rather than silently ignored. Missing pypdf is a reported failure; no fabricated successful check. The workflow installs pypdf from PyPI for this read-only parser.

Official source: https://www.sec.gov/Archives/edgar/data/919160/000114336226000444/KBTY111026.pdf
