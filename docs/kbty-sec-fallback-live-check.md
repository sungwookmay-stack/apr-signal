# KBTY SEC 공식 대체 검색 검증

최초 SEC submissions API 접근이 GitHub Actions에서 거절되어, SEC 공식 full-text 검색 API를 2차 경로로 추가했습니다.

이번 실행은 KBTY 시리즈 관련 공시만 조회하고, SEC 결과에 타 펀드가 섞이면 배제합니다. 모든 결과는 원문 또는 SEC index header로 검증되기 전까지 KBTY 최신 확정 공시로 표시하지 않습니다.

이 작업은 무료 SEC 조회만 수행하며 Amazon·Google Trends·BSR/API.SH를 재수집하지 않습니다.
