# 오후 16:00 기술지표 + 뉴스 첫 검증

- 오전 07:30 기존 전체 수집은 유지.
- 오후 16:00에는 APR 실제 일봉, 기술지표, 현지 뉴스만 갱신.
- Scrape.do, API.SH, 환율, 관세청 운임 재호출은 하지 않음.
- 당일 공개 종가가 확보되지 않으면 최종 검증 거래일을 그대로 표시.
- 작업 후 `data/status.json` 의 `afternoon_verified_same_day`, `technical_last`, `price_last` 를 확인.
