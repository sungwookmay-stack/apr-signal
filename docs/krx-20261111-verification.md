# KRX 2026-11-11 verification and regular-session schedule

Verified on 2026-11-12 KST. No new KRX values were invented or imported.

- Existing `data/flows.json` contains 11 November individual/foreign/institution net shares from the Naver KRX-only public-page fallback, observed 11 November 12:18 UTC. Cash amounts are close-times-shares estimates, **not official KRX net trading values**. Pension and short observations remain unavailable.
- The direct HTTP request from the execution environment returned HTTP 403.
- The cloud browser loaded the official KRX site. Following home → 주식 → 거래실적 → 투자자별 거래실적(개별종목) displayed **로그인 또는 회원가입이 필요합니다.** The detached outerLoader form is accessible but APR lookup returns no data. It is not an authenticated data connection.
- Only the dot cloud computer is currently connected; no existing authorized personal-browser session was available. No credentials/cookies were copied, and no access controls were bypassed.
- Official entry: https://data.krx.co.kr/contents/MDC/MAIN/main/index.cmd
- Investor screen reference: https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd?screenId=MDCSTAT023
- Possible next step is an authorized KRX login followed by APR-specific export and source/unit/date verification. A manual export does not establish recurring authenticated collection. Do not promise a KRX OpenAPI key covers this table.

The workflow now **attempts** the existing free flow collector at 16:30 KST as well as the existing 20:30 and 07:30 checks. The 16:00 technical/news run remains unchanged. Amazon, Google Trends, DART and other morning-only collections are not added to 16:30. GitHub scheduling may be delayed. Original source barriers and missing-value handling are preserved.
