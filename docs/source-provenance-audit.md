# Source provenance corrections (2026-11-11)

## Corrected
- Ownership watchpoint headline and history now use the same latest reporter and filing type. An isolated observation does not borrow another person's history.
- Securities lending labels and metadata follow the actual latest row. Current saved observations are from Financial Services Commission public API 15059612, not the KSD 15157426 link formerly displayed.
- Investor flow metadata follows the latest observed source; Naver net-shares times close estimates are not described as official net trading value.
- KBTY price is explicitly Yahoo unofficial daily price. AUM extraction is limited; NAV and APR holdings require sourced manual CSV inputs. Missing inputs do not establish that the issuer has not published data.
- KBTY current listing status is unknown if the fetched text does not match a verified announcement or the issuer fetch fails. AUM is a balance, not a direct measure of inflows.

## Remaining limits
- KBTY SEC fetch failure is already exposed. This change does not restore that source or create a holdings feed.
- KITA East Coast latest references are secondary KITA citations, clearly segregated from directly checked KITA observations.
- News localization translates headlines and adds category context; it is not article-body verification.
- EPS/BPS and online/offline retail corrections are separate concurrent work.

## Verification
Python unittest suite, all JavaScript smoke suites, JavaScript syntax and diff whitespace checks. New regression tests cover mixed ownership reporters/types and unverified KBTY listing status. No paid collection, new credentials, or production collection triggered.
