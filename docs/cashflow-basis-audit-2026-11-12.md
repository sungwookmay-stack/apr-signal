# Cash-flow basis audit (2026-11-12 KST)

2025 Q1/Q2 CFO used 2026 comparative restatements while Q3/Q4 used the original 2025 reporting basis. These values were individually real but the mixed series understated annual CFO by 30.46억원. Restore the original 2025 quarterly series; keep the new-basis comparative YTD values explicitly as audit metadata, not silent overrides.

| Period | Original CFO YTD KRW | Tangible capex YTD KRW | Receipt |
|---|---:|---:|---|
|2025Q1|53,510,011,149|3,562,216,085|20250515001164|
|2025H1|119,113,231,292|7,700,083,308|20250814001828|
|2025Q3|184,977,146,393|11,239,150,045|20251114002319|
|2025FY|341,046,397,295|15,411,405,167|20260323001257|
|2026Q1|4,270,874,944|5,072,895,132|20260515001577|
|2026H1|86,404,149,570|16,794,134,780|20260814002503|

Source for each receipt: `https://dart.fss.or.kr/dsaf001/main.do?rcpNo=RECEIPT`, consolidated cash-flow statement, not separate financials. 2025 originals independently inspected in official APR-hosted report PDFs. 2026 DART cash-flow sections independently retrieved and inspected.

2026 Q1 report's comparative 2025 Q1 CFO is 51,547,432,619 KRW; 2026 H1 comparative CFO is 116,067,068,380 KRW. Do not combine these restated comparatives with original 2025 Q3/FY. Cross-year CFO/cash-conversion comparisons require a consistent classification basis (2026 K-IFRS1118 change).

Quarter CFO changes (억원): Q1 515.47 -> 535.10; Q2 645.20 -> 656.03. All later CFO values unchanged. Q3 tangible capex gap filled as (11,239,150,045 - 7,700,083,308)/1e8 = 35.39억원. FCF proxy Q1 499.48, Q2 614.65, Q3 623.25. This proxy excludes intangible acquisition and is not a formally reported FCF measure. 2026 Q3 remains unknown.

Regression checks: per-quarter YTD subtraction, annual and H1 reconciliation, all cash-conversion/FCF formulas, restatement isolation, and unknown preliminary quarter. Source payload carries original and comparative provenance.
