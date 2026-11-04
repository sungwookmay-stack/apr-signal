# APR SIGNAL — 에이피알 글로벌 투자 모니터

**무료 클라우드 웹사이트** · GitHub Pages + GitHub Actions · 스마트폰/PC 상시 접속 · Python 표준 라이브러리

이 저장소는 에이피알(278470) 관련 **확인 가능한 시장·수요·영업 정보를 누적**하고, 기술적 분석을 학습·관찰하기 위한 개인용 공개 대시보드입니다. 매매 주문/알림봇이 아닙니다.

## 1. 화면 구성

| 메뉴 | 내용 | 데이터 공개 시점 |
|---|---|---|
| 시장 · 환율 | APR 종가 KRW / 같은 날짜 환율로 환산한 USD, USD/KRW, EUR/KRW; 2026년 5월부터 월말·월평균 비교 | 자동 수집 시도, 주가·FX 공급사 제한 시 상태 표시 |
| 기술적 분석 | 볼린저밴드(20일, 2σ), 일목균형표(9/26/52, 시프트26), MA 20/60/200, RSI14, MACD(12/26/9), ATR14, 거래량 비율, 매수/매도/추가매수 **참고 조건** | **OHLC·거래량이 충분한 200거래일 확보 후** 조건 판단 |
| 글로벌 수요 | US, GB, DE, FR, IT, ES, CA, JP, AE, SA, EG Amazon BSR; QA, KW, CL 포함 14개국 Google Trends | API.SH 무료키 연결 후 자동; CSV/수동 기록도 가능 |
| KBTY ETF | NYSE Arca KBTY 거래가, AUM, NAV, 에이피알 비중·보유주식수, 펀드 공시 상태 | 실제 상장·운용사 공개 이후 |
| 칠레 · 신사업 | **칠레 스페인어 뉴스**와 KINEGUN / PN 스킨부스터 / 의료용 HIFU·RF / 일본·중동 진출 | Google News RSS·검증된 사건 연표 |
| 물류 · 실적 | 해상운임 지수, KITA 해·항공 자료 링크, 북미·유럽 채널·분기 성장률 | 항로별 공개 자료 및 공시·어닝콜 |

> 실측치가 없는 곳에는 **0을 넣거나 과거 데이터를 만들어 표시하지 않습니다.** 구글 트렌드는 국가·기간·검색어 묶음 안에서 0–100으로 정규화된 관심도이며 절대 검색량이 아닙니다. Amazon BSR은 카테고리별 순위이지 실제 판매 수량이 아닙니다.

## 2. PC가 필요 없는 사이트 만들기

**이미 연결한 GitHub 계정에서 별도 저장소를 만들어 사용합니다.** 기존 `job-radar` 같은 다른 프로젝트는 수정하지 않습니다.

1. [GitHub의 새 저장소 만들기](https://github.com/new)에 접속합니다.
2. 저장소 이름 예: `apr-signal`. **Public**로 만듭니다. 코드에는 비밀키·매수단가·계좌정보를 넣지 않습니다.
3. 이 ZIP 내부 파일과 폴더를 저장소 최상단에 그대로 올립니다. **`.github/workflows/update-and-publish.yml` 폴더 구조가 반드시 유지**되어야 합니다. 파일을 ZIP인 상태로 한 개만 업로드하면 실행되지 않습니다.
4. 저장소 **Settings → Pages → Build and deployment → Source: GitHub Actions**를 선택합니다.
5. **Actions → APR SIGNAL - free data refresh and Pages → Run workflow**를 실행합니다. 첫 실행 후 페이지 주소는 Settings → Pages에서 확인할 수 있습니다.
6. 사이트 주소 예시는 `https://<본인-계정>.github.io/apr-signal/`이며, **실제 주소는 배포 완료 후 GitHub에서 확인**합니다.

> 연결된 GitHub 플러그인으로 작업하는 경우, 사용자가 새 빈 저장소를 만든 뒤 **저장소 주소만 알려주면** 그 저장소에 맞춰 파일을 올리는 방법으로 이어갈 수 있습니다. 이 ZIP을 만들었다는 사실만으로 온라인 사이트가 배포된 것은 아닙니다.

### Git 명령어가 편한 경우

새로 만든 빈 저장소를 대상으로 해당 경로에서 다음을 실행합니다. `OWNER`는 자신의 GitHub 사용자 이름으로 바꿉니다. Git 설치가 되어 있어야 합니다.

```bash
git init
git branch -M main
git add .
git commit -m "Initial APR SIGNAL dashboard"
git remote add origin https://github.com/OWNER/apr-signal.git
git push -u origin main
```

## 3. 실제 자동 수집이 필요한 경우 — 무료 API 키 한 개

**선택사항이지만 적극 추천:** [API.SH](https://api.sh/google-trends-api) 회원가입 → 이메일 확인 → 무료 API 키 발급. 안내 기준 **월 무료 1,000크레딧**, 카드 없이 시작 가능. Google Trends `/google-trends/v1/interest` 호출당 **1크레딧**, Amazon `/amazon/v1/product` 호출당 **3크레딧**, `/amazon/v1/search` 호출당 **1크레딧**. 가격/무료 정책은 공급사에 따라 바뀔 수 있습니다.

- GitHub 저장소 **Settings → Secrets and variables → Actions → New repository secret**
- **Name:** `APISH_KEY` / **Secret:** 발급받은 실제 키
- 키는 **공개 Issue, 파일, 채팅, 프런트엔드 JavaScript에 넣지 않습니다.** Actions 서버에서만 사용됩니다.
- 가능하면 API.SH 키별 **허용 엔드포인트 제한 + 월 크레딧/요금 상한**을 설정하고 **유료 자동충전은 활성화하지 마세요.**
- 코드 자체에도 **한 달에 최대 750크레딧의 호출 *시도*** 한도를 걸어둡니다. 다른 앱에서도 같은 키를 쓰면 사용량이 합산될 수 있으므로 무료 유지의 최종 책임은 API.SH 계정 설정에 있습니다.

**실행 빈도 (예약 작업 매일 09:17 한국시간 부근):** Google Trends 전 지역 최대 14개국 **이틀에 한 번** 한 번에 4~5검색어씩; Amazon 한 개국에서 `medicube` 상품 검색으로 검증된 ASIN 발굴 **하루 한 번**; 확인된 ASIN 최대 4개를 순환하며 카테고리 BSR 확인 **하루 한 번**. 제공처가 BSR을 숨긴 상품은 수치를 저장하지 않습니다. 약 14×15 + (1+3×4)×30 = **600크레딧/30일**의 정상 최대 작업량을 예상하지만, 하드한 750 제한과 공급사 내 무료 사용 상한을 모두 사용해야 합니다. 

API.SH 응답 형태는 공개 문서에 맞춰 구현했지만 **실제 API 키 없이 응답을 받아 최종 통합 테스트를 한 것은 아닙니다.** 최초 사용 후 `물류·실적 → 데이터 수집 상태`의 오류 항목을 확인해 주세요.

키가 없다면 FX·주가·뉴스 등은 공개 출처 기반으로 시도하고, Google Trends는 공식 CSV, Amazon BSR은 `imports/amazon_observations.csv` 기록을 사용합니다.

API.SH 공식 문서: [Trends interest](https://api.sh/docs/google-trends-interest) / [Amazon search](https://api.sh/docs/amazon-search) / [Amazon product](https://api.sh/docs/amazon-product).

## 4. 2026년 5월부터의 과거 데이터

- **주가**: 네이버 금융 공개 차트 → 네이버 금융 시세 JSON → Yahoo Finance 순서로 시도. **2025년 7월부터** 충분한 과거 일봉을 받아 200일 이동평균 워밍업에 사용하지만, 화면에는 **2026년 5월 이후만 표시**합니다. 주가 제공처 접근이 막히면 과거 마지막 확인값을 보유하며 오류를 기록합니다.
- **환율**: 무료 ECB(유럽중앙은행) 공식 과거 참조환율 ZIP·CSV(달러/원은 ECB EUR/KRW ÷ EUR/USD로 산출), 실패 시 Frankfurter 보조, 일별. **서울외국환중개 실시간 매매기준율과 다른 데이터**이므로 출처를 혼동하면 안 됩니다.
- **USD 기준 APR 주가**: `해당 일 APR 원화 종가 / 그 날 USD/KRW 참조환율`입니다. 환율 발표가 쉬는 날은 최대 5일 이내의 가장 최근 FX 기준값만 허용하고 날짜를 함께 기록합니다.
- **Amazon BSR**: 과거 기록은 처음부터 모두 가져올 수 없습니다. 무료 API 설치일 이후 실측치부터 누적합니다.
- **Google Trends**: 키가 있다면 API 요청 기간을 **2026-05-01~현재**로 고정하고 국가별 검색어 세트를 한 번에 정규화된 형태로 갱신합니다. 각 시점의 개별 0~100 수치를 억지로 합치지 않습니다.
- **현재 ZIP의 초기 데이터**: 주가 50거래일(2026-08-20~2026-11-03) 검증용 스냅샷만 포함되어 있습니다. **5월부터 전체 기록·실제 FX·완성된 일목/MA200은 첫 온라인 수집 성공 후에만 표시됩니다.**

## 5. 분기 ETF · 신사업 데이터의 성격

**KBTY:** 2026-11-04 기준 11월 둘째 주 상장 예정, 예상 25종목, 보수 0.55%로 안내되어 있습니다. 상장 전인 현재의 `가격`, `AUM`, `APR 편입 비중`, `APR 보유 수량`은 알 수 없어 **빈칸**으로 시작합니다. 거래가격은 Yahoo Finance 비공식 시세를 보조로 확인하고, AUM·보유종목은 운용사 공식 파일 또는 검증된 자료를 나중에 입력해야 합니다. 확인된 자료가 있으면 `imports/kbty_aum.csv` 및 `imports/kbty_holdings.csv`에 출처 URL과 함께 추가합니다.

**칠레 스킨부스터 / HIFU:** Google News RSS를 스페인어/현지 국가 설정으로 탐색합니다. 웹 기사 수 자체는 실판매가 아니므로 출시·허가·클리닉 취급·재주문을 분리합니다. 공시에서 확인된 주요 사건은 `config/verified_events.json`에 날짜/원문 링크로 보관합니다.

**Ulta·Target·Boots·중동 유통:** 실제 매장별 셀스루 및 매출액은 일반적으로 공개되지 않습니다. 사이트 링크를 제공하며 공개되어 확인된 리뷰·상품 수·취급현황만 `imports/retail_observations.csv`에 날짜와 근거 URL을 붙여 누적합니다.

**KITA 운임:** 링크 [해상](https://www.kita.net/shippers/logisticsFare/logisticsSeaFare.do) / [항공](https://www.kita.net/shippers/logisticsFare/logisticsAirFare.do). 안정적 무상 API가 확인되지 않아 사이트가 월별 공개 통계를 참고하고 KITA 최신값은 원문 조회를 제공합니다. 이는 APR 실제 계약운임·물류비가 아닙니다.

## 6. 투자 신호는 어디까지 참고하나

- `indicator_engine.py`에서 일봉 200개 이상 및 정상적인 OHLC·거래량 확인 후에만 종합적인 매수/매도/추가매수 **관찰**을 허용합니다.
- 볼린저 하단 이탈·RSI 과매도만으로 **물타기 신호를 만들지 않습니다**. 일목 구름·장기 추세·모멘텀·반등을 교차 확인합니다.
- 기술지표는 과거값을 기술할 뿐 예측 정확도는 검증되지 않았습니다. 실전 적용 전에 비용·슬리피지·과최적화를 반영한 백테스트가 필요합니다.
- `종가 - 2×ATR`은 변동성 폭을 보여주는 참고선이며 개인 계좌의 손절 가격이 아닙니다.

## 7. 프로젝트 구조

```text
index.html                         반응형 UI
assets/style.css                   모바일·데스크톱 스타일
assets/app.js                      그래프와 데이터 표
build_data.py                      무료 공개 출처 수집·뉴스·ETF
optional_free_api.py               선택형 API.SH Trends + Amazon, 월 750 시도 크레딧 상한
update_data.py                     2026-05부터 APR KRW/USD·FX·해상운임
indicator_engine.py                볼린저·일목·MACD·RSI·ATR + 다중 조건 검사
seed_data.py                       초기 검증 스냅샷 준비
data/*.json                        실제 수집된 시계열과 상태, 처음에는 결측값 있음
config/markets.json                14개국·공식 판매처 설정
config/verified_events.json       칠레·HIFU 검증된 사건
imports/*.csv                      무료 수동 입력·공식 데이터 업로드 양식
.github/workflows/update-and-publish.yml   매일 클라우드 수집·저장·배포
tests/test_monitor.py              기술적 분석과 결측치·API 파싱 테스트
```

## 8. 직접 테스트

```bash
python -m unittest discover -s tests -v
python seed_data.py
python -m http.server 8787
```

브라우저에서 `http://127.0.0.1:8787`로 개발용 로컬 미리보기 가능. **배포 후에는 PC·Anaconda 실행이 필요하지 않습니다.**

주의: 공짜 GitHub Pages 저장소는 **공개**됩니다. GitHub Actions의 실행 시점은 예약 시간보다 늦어질 수 있습니다. 데이터 제공처·API의 차단, 무료 정책 변경, 주식 분할·수정주가 이슈, 휴장일, 환율 고시 시차는 보고서의 수집 상태를 반드시 확인하세요.


## Beauty 상위 순위 집계 (2026-11-04 추가)

- 대상: 미국 Amazon Beauty는 매일, 다른 10개 마켓은 하루 2곳씩 순환 관측
- 자료: API.SH `/amazon/v1/bestsellers?category=beauty&list=best_sellers`의 1·2페이지
- 집계: 고유 ASIN 중 제목/브랜드에 `medicube`가 확인되는 항목을 합산
- **중요:** API 제공 문서에 따르면 두 페이지에 약 50개만 제공될 수 있음. 1~100위를 모두 관측하지 못한 날의 수치는 **'확인된 최소 품목 수'**로만 표시함. 실제 전체 Top100 합계를 추정하지 않음
- 추적: 날짜별 확인된 수, 실제 확보한 순위 항목 수, 동일한 관측 범위일 때의 신규 진입·이탈, 상품별 순위 및 ASIN
- 최초 수집 이전 날짜의 순위를 소급해 만들지 않음
- 무료 예산: Beauty 상위 목록 최대 하루 6크레딧(3개국 × 2페이지), 아마존 기존 개별 BSR 조회 하루 최대 2개로 조정. API.SH 모든 기능 합산 월 **750 크레딧 시도 상한**을 유지. GitHub 코드 변경 시 수집 API를 호출하지 않음
- 1회 확인용 갱신은 GitHub Actions 수동 실행 또는 특별한 `[collect-now]` 표시 커밋으로 수행하고, 평상시는 한국시간 매일 07:30 자동 갱신. GitHub 예약 실행은 지연될 수 있음
- 국가별 카테고리 정의가 다르면 단순 품목 수를 비교해 시장점유율이라고 단정할 수 없음


- 2026-11-04: 아마존 부분 베스트셀러에서 확인된 ASIN을 BSR 추이와 연결하고, Ulta/Target/Boots 및 독립 주간 미국 Top100 참고지표를 근거·기준일과 함께 표시하도록 보강. 공개 판매처 갱신이 실패하면 마지막 확인값을 보존한다.

## 영국 등 Top 100 누락 보완: 무료 대체 API (2026-11-04)

**왜 영국 상품이 0개로 보였나?** 11월 4일 초기 API.SH 자료는 US/SA/EG 3개국만 저장되었고 영국은 미수집이었다. 따라서 영국은 0개가 아니라 미수집이다. 일부 아마존 목록은 페이지당 순위 50개 중 약 30개 상품만 제목을 제공한다. 순위와 ASIN만 있는 항목은 브랜드를 알 수 없어서, 숫자를 0개 혹은 전체 미진입으로 확정하면 오류가 된다.

- 우선 지역: **미국·영국 매일**, 그 외 아마존 9개 마켓 중 하루 1개국 순환
- 기존 API.SH: 무료 계정 키 `APISH_KEY` 유지, 부분 목록 제공 시 **최소 확인 개수**만 집계
- 선택형 Scrape.do: [무료 플랜](https://scrape.do/pricing/)의 월 1,000 크레딧(신용카드 불필요); [Best Sellers API 문서](https://scrape.do/documentation/amazon-scraper-api/bestsellers/). [GitHub Actions Secret](https://github.com/sungwookmay-stack/apr-signal/settings/secrets/actions)에 `SCRAPEDO_TOKEN` 등록 시 `scrapedo_bestsellers.py` 자동 활성화. 코드에는 토큰을 넣지 않음.
- Scrape.do 아마존 Beauty 1, 2페이지는 각각 랭킹 1~50, 51~100의 **전체 ASIN 순위**를 제공하지만, 제목은 일부만 제공. 확인된 종목의 제목과 이전에 검증한 ASIN 자료를 교차 대조한다.
- **두 개의 독립적인 완전성 표식:** `rank_coverage_complete`는 1~100위 ASIN 확보, `coverage_complete`는 ASIN에 대한 상품명/브랜드까지 100개 검증한 경우만 `true`. 둘 다 확인하지 못하면 **메디큐브 최소 확인 품목 수**로 표시, 미수집/미진입 구분.
- 공급사 요청 실제 비용과 무료 플랜은 변경될 수 있다. Scrape.do 코드는 요청당 3크레딧 보수적 예약·월 690크레딧 자체 한도로 차단하고 기본 `super=false`를 유지하며 프로바이더 `Scrape.do-Request-Cost` 헤더도 기록한다. 사용량은 `data/scrapedo_usage.json`에 누적. 가입 후 실제 계정에서 호출비용 및 무료 사용량 검증 필요.
- **다른 참고자료:** [MetricsCart 영국 2026년 9월 분석](https://metricscart.com/bestseller-reports/amazon-uk/categories/Beauty/)에는 그달 베스트셀러 목록에 등장한 메디큐브 **서로 다른 15종**이 기록됐다. 이는 월간 관측치이며 특정 하루의 동시 Top 100 진입 15종이라는 뜻이 아니다. 사이트 `data/reference_signals.json`의 `amazon_monthly`에 따로 표기한다.
- 미국·영국 외 마켓 역시 현재 확인 기록이 없으면 **미수집**이라고 표시하며 임의의 0개를 만들지 않는다.
