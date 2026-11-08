# APR 주식 추적기 / OpenDART 최초 실수집 확인

- GitHub Secret `DART_API_KEY`를 GitHub Actions 환경변수로만 전달
- 실제 OpenDART 재무(연결)/대주주·임원/배당·자기주식 API 결과 검증
- 미국 공식 상품 상세페이지의 리뷰·평점 관측도 무료 갱신
- SCRAPEDO_TOKEN/APISH_KEY는 이 전용 실행에서 사용하지 않음
- 2025년 6월부터의 시세·원화/달러 밴드, 별도 RSI/MACD 등 기존 공개 화면도 배포
- API 응답이 없으면 공란·접근 실패 표시; 과거 보고서 값을 임의 보정하지 않음
