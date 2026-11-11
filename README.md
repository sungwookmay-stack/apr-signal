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


## Amazon Beauty 11개국 무료 일별 수집 (2026-11-04 최신 운영안)

**무료 운영이 제1원칙입니다.** Amazon BSR이 비어 있던 API.SH 개별 상품 조회는
Scrape.do 토큰이 설정된 동안 실행하지 않고, Google Trends 수집은 기존 API.SH 키를 유지합니다.
새로운 유료 구독·유료 프록시·자동 충전은 사용하지 않습니다.

- 대상 독립 Amazon 마켓 11개국: US, GB, DE, FR, IT, ES, CA, JP, AE, SA, EG.
  QA/KW/CL은 독립 Amazon 마켓이 아니므로 Google Trends와 별도 유통 채널로 관리합니다.
- **07:30 KST 매일:** Scrape.do Best Sellers API의 국가별 Beauty 1·2페이지
  (각 50순위) 수집을 시도합니다. 정상 동작하면 11×2=22요청/일입니다.
- **ASIN 정합성:** 상품 카드에 없는 약 40개/국가의 브랜드는 국가별
  `data/amazon_asin_identities.json`에 검증된 기존 상품명/브랜드를 대조하고,
  미확인 ASIN만 무료 예산 내 PDP API로 추가 확인합니다. 미확인 ASIN은 메디큐브가
  아니라고 가정하지 않습니다.
- **PDP BSR:** Scrape.do 상품 상세페이지의 `best_seller_rankings`를
  `data/scrapedo_pdp.json`에 날짜·국가·ASIN·카테고리별 누적합니다.
  국가별 Beauty Top100 순위와 상품별 세부 카테고리 BSR은 **별도 그래프**입니다.
- **유료 방지:** 무조건 요청당 3크레딧을 먼저 예약한 후, 성공 응답의
  `Scrape.do-Request-Cost` 헤더가 있을 때만 실제 차감량으로 보정합니다.
  실제 비용이 기본 1크레딧을 넘거나 월 900크레딧 보호 상한, 계정 잔여
  20크레딧 이하라면 추가 수집을 자동 중단합니다.
  비용 헤더가 없으면 3크레딧 예약을 유지합니다.
- 월 31일 **가정상** Best Sellers 682 + PDP 최대 124 = **최대 806크레딧**입니다.
  이 계산은 요청당 실제 비용이 1크레딧임이 확인된 경우에만 적용됩니다.
  API가 실패하거나 비용 헤더가 없으면 수집량을 줄여서라도 안전한도 안에서 작동합니다.
- 먼저 수집한 날짜부터 이력이 누적됩니다. 과거 날짜를 임의로 채우지 않습니다.
  국가별 관측 실패/일부 순위 확보는 0건이 아니라 미수집 또는 최소 확인으로 구분합니다.
- 독립적인 Top100 랭크 100개를 받더라도, 상품 정체가 확인되지 않은 ASIN이 남으면
  메디큐브 진입품목 수는 **최소 확인 수**입니다. 진입·이탈은 동일 범위에서
  정체를 모두 확인한 날 사이에만 확정합니다.
- 최신 수집 방식은 `scrapedo_bestsellers.py`, `build_data.py`,
  `assets/app.js`, `tests/test_scrapedo.py` 참조.

### 설정

1. [Scrape.do 무료 플랜](https://scrape.do/pricing/)에서 토큰 발급. 카드 정보 등록이나 유료 업그레이드 불필요.
2. GitHub 저장소 Settings → Secrets and variables → Actions에 `SCRAPEDO_TOKEN`
   을 등록합니다. 토큰은 저장소 파일이나 채팅에 붙여넣지 마세요.
3. 기존 `APISH_KEY`는 Google Trends 수집을 위해 그대로 유지합니다.
4. GitHub Actions → APR SIGNAL - free data refresh and Pages → Run workflow 실행,
   완료 후 **데이터 수집 상태** 및 `data/scrapedo_usage.json`의
   `last_verified_cost`와 `reserved_credits`를 확인합니다.

*참고:* [Scrape.do Best Sellers 문서](https://scrape.do/documentation/amazon-scraper-api/bestsellers/) /
[PDP 문서](https://scrape.do/documentation/amazon-scraper-api/pdp/) /
[요청당 비용](https://scrape.do/documentation/request-costs/).
국가별 카테고리 URL이 다른 경우 `config/markets.json`의 해당 국가에
`amazon_beauty_slug`를 별도로 지정할 수 있습니다. API키를 이용한 국가별
실호출 테스트는 토큰 등록 후에만 가능합니다.

## 현지 뉴스 한국어 제목·핵심 정리 (2026-11-05)

- **칠레·HIFU·중동·KBTY 뉴스**는 원문 제목보다 **한국어 제목과 한 줄 핵심 주제**를 먼저 표시합니다.
- Google News RSS에는 기사 본문 전문이나 실제 본문 요약이 없습니다. 한국어 정리는 **제목 기반**으로만 작성하며, 기사 보도를 매출·인허가 확정으로 표시하지 않습니다.
- 기존 수집된 제목은 `config/news_korean_seed.json`의 직접 검토한 한국어 제목·설명을 사용합니다. 향후 새로운 제목은 별도 키·유료 구독 없이 MyMemory 무료 번역 API를 사용합니다.
- [MyMemory 공식 무료 제한](https://mymemory.translated.net/doc/usagelimits.php): 익명 5,000자/일, 요청당 최대 500 UTF-8 바이트. 코드는 하루 4,000자, 실행당 최대 28회로 제한합니다.
- 외부 번역 서비스가 중단돼도 기존 번역·원문은 삭제하지 않고 번역 대기 상태를 표시합니다.
- 같은 기사(제목과 URL/분류 일치)는 매일 재번역하지 않고 캐시합니다. 일별 예약사용량은 `data/news_translation_usage.json`에 누적됩니다.
- 사이트의 '원문 제목 보기'로 외국어 원제를 펼치고 '현지 기사 원문 확인'에서 보도 원문을 확인할 수 있습니다.
- 매일 기존 07:30 KST 자동 갱신에 포함되며, '[translate-now]' 커밋은 기존 아마존 API를 재호출하지 않고 뉴스 번역만 실행합니다.
- 기사 **본문 기반 상세 요약**은 기사 원문 접근과 검증이 추가로 필요하며, 현재는 제공하지 않습니다.

## 남미 브라질·아르헨티나·칠레 글로벌 수요 (2026-11-05)

- **지역 선택:** 글로벌 수요의 남미 3개국 바로가기와 국가 선택을 제공하고 Google Trends에서 BR·AR·CL 모두 `medicube` 관련 5개 검색어를 관측합니다. BR은 포르투갈어, AR/CL은 스페인어로 조회합니다.
- **Amazon:** BR 독립 마켓 `amazon.com.br`에 대해 Scrape.do Beauty Top 100 1~2페이지 및 개별 PDP BSR을 시도합니다. AR/CL은 독립 Amazon 마켓이 없으므로 Amazon BSR과 Top100 수치를 만들지 않습니다. BR category slug `beauty`는 공급사 실제 응답으로 추가 확인해야 합니다.
- **비용:** Amazon 대상 12개국 × 2페이지 × 31일 + 제품 PDP 최대 4회 × 31일 = **최대 868크레딧** (실제 요청당 1크레딧이라는 전제). 기존 월 900크레딧 안전 상한과 비용 헤더 검증, 무료 잔여량 방어가 유지됩니다. 자동 충전은 하지 않습니다.
- **현지 유통 접점:** 세 나라의 Mercado Livre·Mercado Libre 메디큐브 검색 링크를 제공합니다. 검색 결과 건수는 공식 브랜드 출고·연결매출·실판매량이 아닙니다.
- **현지 뉴스:** 브라질 포르투갈어와 아르헨티나 스페인어 RSS 제목도 탐색하고, 한국어 제목·제목 기반 설명으로 표시합니다. 본문 전문 요약으로 오해하면 안 됩니다.
- **Google Trends:** 국가마다 0~100으로 별도 정규화되므로 브라질 60과 칠레 40을 실제 검색량 1.5배로 해석할 수 없습니다. 과거 시계열은 API가 정상 반환한 날짜만 표시합니다.

공식 자료: [Scrape.do Amazon 마켓](https://scrape.do/documentation/amazon-scraper-api/), [베스트셀러 카테고리](https://scrape.do/documentation/amazon-scraper-api/bestsellers/).

## 미국 관련 뉴스 자동 수집 (2026-11-05)

- **미국 오프라인 유통:** Medicube와 Ulta, Target, Walmart, Costco, CVS, Nordstrom 등 소매점 관련 보도를 탐색합니다.
- **미국 Amazon·온라인:** Medicube의 Amazon, Prime Day, TikTok Shop 관련 보도를 탐색합니다.
- **미국 뷰티기기·신제품:** Medicube AGE-R, Booster Pro, 뷰티기기 및 PDRN 제품 동향을 탐색합니다.
- Google News RSS의 미국 `hl=en-US&gl=US&ceid=US:en`을 사용합니다. 이는 **미국 시장 관련 검색**이라는 의미이며, 모든 기사의 발행사가 미국 언론이라는 보장은 없습니다.
- 신사업 → 현지 뉴스 · 한글 요약 → **미국** 필터에서 최신 보도를 모아 볼 수 있습니다. 원문 제목·원문 링크는 보존합니다.
- 기존 무료 MyMemory 한도 내에서 영어 제목을 한국어로 옮기고, 한 줄 설명은 **기사 제목 및 주제에 근거한 간략 설명**입니다. 원문 기사 본문을 자동으로 읽거나 검증된 매출로 단정하지 않습니다.
- 매일 07:30 KST 기존 GitHub Actions 수집에 포함됩니다. 최초 확인용 `[news-now]` 커밋은 **Google News RSS와 무료 번역만** 실행하며 Scrape.do·API.SH 호출을 실행하지 않습니다. 유료 API는 추가되지 않습니다.

## 미국 뉴스 정합성 및 한국어 품질 (2026-11-05 보완)

미국 관련 뉴스 필터는 미국 시장의 메디큐브·APR 보도를 우선합니다. **브랜드가 제목에 없는 일반 K-뷰티 할인 기사, 캐나다 단독 소식**, 오프라인 입점과 관련 없는 리뷰를 미국 유통 뉴스로 잘못 집계하지 않습니다. 원문 기사 국가와 RSS 지역 설정은 구분합니다.

미국 주요 보도 제목의 한국어 번역은 `config/news_korean_seed.json`에 검토한 표현으로 저장했습니다. 무료 기계번역의 어색한 표현(예: viral → '바이러스성')은 검수형 한국어 제목으로 대체합니다. 4,000자/일 무료 안전 한도와 원문 보존 정책은 그대로 유지합니다.

## 뉴스 하루 2회 · 추가 비용 없이 갱신 (2026-11-05)

APR SIGNAL의 **현지 뉴스/한글 제목 정리**는 다음과 같이 운영합니다.

| 한국시간(KST) | GitHub Actions cron(UTC) | 작업 |
| --- | --- | --- |
| 매일 07:30 | `30 22 * * *` | 종전 전체 수집: APR·환율·운임·Amazon·Google Trends·뉴스 |
| 매일 16:00 | `0 7 * * *` | **뉴스 전용 갱신**: Google News RSS → 새 제목 한국어 번역 → 기존 데이터 업데이트 및 GitHub Pages 배포 |

- 오후 단계는 `build_data.py` 전체 실행을 하지 않고 `collect_news()`만 호출하므로 **Scrape.do·API.SH 크레딧 소비가 늘지 않습니다.** 기존 Amazon 수집 횟수는 하루 1회 그대로입니다.
- GitHub 공개 저장소의 표준 `ubuntu-latest` Actions 실행은 무료입니다. GitHub 예약 워크플로는 상황에 따라 실행이 지연될 수 있습니다.
- MyMemory 비로그인 계정의 공식 무료 한도는 **5,000자/일**이고, 코드의 자체 한도는 **UTC 날짜별 4,000자와 최근 24시간 누적 4,000자 중 더 엄격한 값**입니다. 따라서 한국시간 오전·오후 작업이 UTC로 다른 날짜여도 두 번의 번역량을 별도 무료 한도로 취급하지 않습니다.
- 이미 번역된 기사 제목은 재번역하지 않습니다. 한국어화 대기 기사는 다음 무료 한도 내에서 시도하며, 원문은 항상 보존합니다.
- 이전 `data/news_translation_usage.json`은 누적 사용량만 저장하므로, 최초 업그레이드 시 최근 사용량을 보수적으로 계산해 일시적으로 번역 건수를 제한할 수 있습니다. 기사 자체는 수집됩니다.
- 기존 `[news-now]` 수동 호출 및 전체 `workflow_dispatch` 동작은 보존합니다. 오후 추가 워크플로는 새 유료 서비스나 개인 PC 상시 실행을 요구하지 않습니다.

공식 참고: [GitHub Actions 공개 저장소 무료](https://docs.github.com/en/actions/concepts/billing-and-usage) · [MyMemory 익명 번역 5,000자/일](https://mymemory.translated.net/doc/usagelimits.php).

## 16시 장마감 에이피알 기술적 분석 추가 (2026-11-05)

**뉴스 하루 2회 무료 운영**에 기술적 분석도 오후 갱신하도록 보완했습니다.

| 한국시간 | 데이터 수집 | 기술적 분석 |
| --- | --- | --- |
| 오전 07:30 | 주가·환율·운임·Amazon/BSR·Trends·뉴스 등 기존 전체 자료 | 저장된 확인 일봉으로 갱신 |
| 오후 16:00 | **에이피알 종가·OHLCV 공개 일봉 + 글로벌 현지 뉴스만** | **SMA20/60/200·RSI14·MACD·볼린저밴드·일목균형표·ATR14 등 재계산** |

- 오후 16시에는 `afternoon_refresh.py`만 실행하며, Naver/Yahoo 공개 일봉과 Google News RSS, 무료 한도 내 제목 번역을 사용합니다.
- 오전 전체 갱신은 변경하지 않습니다. 오후에는 `SCRAPEDO_TOKEN`과 `APISH_KEY`를 전달하지 않으며, `update_data.update(refresh_fx=False, refresh_freight=False)`로 오후에 **ECB 환율·관세청 운임 데이터를 재조회하지 않습니다.**
- 공개 시세 제공처에 당일 확정 일봉이 아직 없으면 이전 검증 일자를 유지하고, `status.json`의 `afternoon_price_date`·`afternoon_verified_same_day`·`afternoon_note`로 구분합니다. 당일 일봉이나 가격을 임의로 만들지 않습니다.
- 오후 지표와 신규 뉴스는 `data/market.json`, `data/technical.json`, `data/status.json`, `data/bootstrap.js`에 반영됩니다. 오전에 수집한 글로벌 수요·BSR·ETF·운임 기록은 보존합니다.
- GitHub Actions 예약 실행은 16:00보다 늦게 시작할 수 있고, 한국 주식시장 휴장일에는 새로운 당일 봉이 존재하지 않을 수 있습니다.
- 전체 갱신을 다시 실행하지 않고 오후 경로만 검증하려면 `[afternoon-now]` 표시 커밋을 사용합니다. 기존 `[news-now]`는 뉴스 전용으로 유지합니다.

## KBTY SEC EDGAR 공시 · 한국어 정리 (2026-11-06)

**KBTY ETF 화면**에 미국 SEC EDGAR 제출자료의 한글 설명과 투자 체크포인트를 추가했습니다.

### 확인된 주요 공시
| 제출일 | 공시 유형 | 투자자 관점 |
| --- | --- | --- |
| 2026-07-10 | 485APOS | Guinness Atkinson Funds의 K-Beauty ETF 신규 시리즈 등록 변경신고. 초기 투자설명서는 지수·보수 등 일부 공란이었으며, 실제 거래 개시를 뜻하지 않음 |
| 2026-09-22 | 485BXT | 기존 등록신고의 효력 발생일을 9월 30일로 지정하기 위한 서류. 상장일 또는 첫 거래일 확정 근거는 아님 |
| 2026-10-28 | 485BPOS | Indxx K-Beauty Index 추종, 총보수 0.55%, 순자산 등 최소 80% 투자, 미용기기·스킨부스터까지 포함하는 가치사슬 전략 등 상세 명시 |

- KBTY는 **미국 SEC 등록·상장 예정·실제 거래 개시·운용사 보유종목 공개**를 서로 다른 단계로 추적합니다.
- SEC 2026년 10월 28일 문서상 주요 위험은 **한국시장·업종 집중, 원/달러 환율, 한국과 미국의 장 시간 차이에 따른 NAV 괴리, 설정·환매의 현금 이용** 등입니다.
- 지수에 특정 기업이 포함될 수 있다는 설명만으로 **에이피알(278470)의 실제 편입비중·매입주식 수·순매수액**을 산정하지 않습니다. 이 값은 운용사의 날짜가 표시된 구성종목·AUM 자료가 확인된 경우에만 기록합니다.
- `config/kbty_sec_registry.json`에는 **SEC 본문을 검토한 세 공시의 한국어 설명**과 출처 URL을 저장합니다.
- 매일 **오전 07:30 KST** 기존 GitHub Actions의 무료 SEC 확인 단계가 `https://data.sec.gov/submissions/CIK0000919160.json`에서 Guinness Atkinson Funds의 제출 목록을 조회합니다.
- **중요:** SEC 신고 주체 CIK 0000919160에는 KBTY 외 다른 펀드도 들어 있습니다. `kbty_sec.py`는 해당 공시의 SEC index header에서 **KBTY 시리즈 `S000109351`가 확인되는 경우에만** KBTY 새 공시로 등록합니다.
- 자동 감지되는 새 서류는 본문을 완전히 검토한 것처럼 요약하지 않고 **공시 종류의 한국어 설명**과 원문 링크만 제공합니다. SEC가 403·429 또는 연결 오류를 반환해도 이전의 검증 공시는 보존하며 '자동 SEC 접근 실패'로 표시합니다.
- SEC 전용 확인이 필요하면 `[sec-now]`로 **SEC 제출 목록만** 갱신할 수 있습니다. 오후 16:00의 무료 뉴스·기술지표 갱신은 그대로이며, SEC 확인을 위해 Scrape.do·API.SH를 추가 호출하지 않습니다.
- 사이트 원문 데이터: `data/kbty_sec.json`. `last_successful_check_utc`가 비어 있으면 **최신 SEC 제출내역 전체가 확인됐다는 뜻이 아닙니다**.
- SEC User-Agent에는 저장소의 공개 문의 주소를 사용합니다. 필요하면 운영자가 GitHub Variables / 환경변수 `SEC_USER_AGENT`에 자신이 관리하는 연락처가 포함된 값을 설정할 수 있습니다. 비밀키는 필요하지 않습니다.

공식 SEC 원문: [7월 등록](https://www.sec.gov/Archives/edgar/data/919160/000121390026077251/ea0297356-01_485apos.htm) /
[9월 효력일 조정](https://www.sec.gov/Archives/edgar/data/919160/000121390026101996/ea0306094-02_485bxt.htm) /
[10월 투자설명서](https://www.sec.gov/Archives/edgar/data/919160/000121390026113359/ea0306550-01_485bpos.htm).

### SEC 자동 접근 제한 시 무료 대체 경로

KBTY SEC 첫 GitHub Actions 실조회에서 SEC submissions JSON 호스트가 HTTP 오류로 차단되는 사례를 확인했습니다. 이를 보완하기 위해 `kbty_sec.py`는 SEC 공식 **Full-Text Search (efts.sec.gov)** API를 2차 경로로 사용합니다.

- 1차: `data.sec.gov/submissions/CIK0000919160.json`
- 2차: `efts.sec.gov/LATEST/search-index`, `"Guinness Atkinson K-Beauty ETF"` 검색 + 신탁 CIK 0000919160 확인
- 새 공시 게시 전: 해당 공시의 SEC index header에 **정확한 시리즈 S000109351**가 있는지 확인
- HTTP 차단·헤더 검증 실패 시 KBTY 신규 공시로 자동 인정하지 않고 상태와 마지막 정상 검증일을 분리
- 자동 추가분은 **서식 기준 개요**일 뿐 본문을 정밀 검토한 요약이 아닙니다. ETF의 실제 APR 보유량은 계속 원문 공식 운용자료만 사용합니다.

SEC의 두 호스트가 모두 차단되는 환경에서는 새 공시 자동 탐지가 실패할 수 있으며, 이는 **비용 문제가 아니라 접근성 한계**입니다. 사이트에는 마지막으로 확인한 공식 공시 3건과 접근 실패 상태가 그대로 유지됩니다.

KBTY SEC 페이지에는 **KBTY 시리즈 S000109351과 직접 관련된 것으로 확인한 공시만** 표시합니다. 다른 펀드 또는 별도 운용사의 13F 기관 보유주식 보고서는 포함하지 않습니다. SEC 자동 조회 실패 시 최신 공시 누락 가능성을 표시합니다.

## APR SIGNAL 2.0 · 재무·유통·밸류에이션 · 디자인 (2026-11-08)

- **화면 구성:** `재무·밸류에이션`(`#financials`)과 `투자 가설·오프라인`(`#theses`) 탭을 추가하고, `글로벌 판매 수요`(`#demand`) 상단에 국가별 주요 Google Trends 변화 항목을 보여줍니다.
- **디자인:** [APR 공식 기업 사이트](https://www.apr-in.com/)의 화이트/블랙·넓은 여백·선명한 제목 스타일을 참고한 `assets/apr_theme.css`. 단, 사이트는 공식 APR과 무관한 독립 리서치 도구이며 회사 공식 로고·사진·레이아웃을 복제하지 않았습니다.
- **연결 분기실적:** `config/apr_financial_source.json`으로 사용자 제공 2025H1·2025Q3·2026Q1·2026H1 보고서와 APR 2025FY 공식 사업보고서를 비교하고, `financial_engine.py`로 재무비율·재고회전일수·TTM 참고 ROE를 계산합니다. 2025Q4 비용·현금흐름은 2025FY-3Q 누계. 2026Q3 매출·영업이익은 잠정자료이므로 3Q 광고·판매수수료·재고를 만들지 않습니다.
- **ROIC:** 확인되지 않은 운전자본·이자부채·조정 세율에 근거한 허위 ROIC는 산출하지 않습니다. ROE 참고치도 연결 총자본 기준 대리지표로 별도 명기합니다.
- **원화·달러·PER/PBR:** 2025-06-02부터 확보한 공개 APR 일봉 및 같은 날 ECB 참조환율을 함께 표시합니다. PER은 15·25·35·45·55배, PBR은 5·10·15·20·25배 밴드입니다. 주당순이익·BPS를 실제 **공시일 이후부터** 적용하며, 과거 주가에 미래 재무를 소급하지 않습니다. EPS는 원문 검증 기본 TTM 기준(희석 EPS 또는 미래 컨센서스 아님).
- **Target 오류 조치:** 과거 Target 카테고리 9개 상품과 '104k+ 구매' 배지는 브랜드 전체 상품 수/실제 POS와 범위가 달라 **추이 계산에서 제외**합니다. 수집기가 공식 브랜드 페이지를 먼저 확인하고 실패 시 제한된 카테고리 페이지만 보조 조회합니다. 타깃 사이트가 JavaScript·접근 제한으로 공개되지 않으면 결측을 유지합니다.
- **오프라인 대리지표:** Ulta Medicube 등록 SKU, Online Only SKU, Only at Ulta 표기, Target 공식 브랜드 등록 SKU(확인된 경우), Boots 공식 검색 성장 안내, 제3자 미국 Amazon Beauty Top100 관측치를 **원본·관측일별로 따로** 누적합니다. 실제 점포별 매출·재주문/POS는 공시 없이는 추정하지 않습니다.
- **투자 가설 3개:** 프리미엄 밸류에이션 정당성, 확장 과정의 마진 유지, 미국 초도 입점 후 반복 수요를 각 지표와 연결합니다. 지표에 검증값이 없으면 '확인 필요'로 둡니다.
- **Google Trends 알림:** `trend_signals.py`가 동일 국가·키워드·정규화 시계열의 최근 평균(일간 7회/주간 4회)을 과거 평균(일간 28회/주간 8회)과 비교합니다. **8p 이상** 변화 + 상승 **35% 이상** 또는 하락 **30% 이상** + 분산·지속성·최소치 기준을 모두 충족해야 강조합니다. 국가별 최대 2개 대표 신호를 표시합니다. 매출·절대 검색량·국가 간 규모를 뜻하지 않습니다.
- **무료 자동 갱신:** 기존 07:30 전체 수집과 16:00 뉴스·기술적 지표는 유지합니다. `build_research_data.py`는 **기존 보고서와 이미 수집된 Trends**를 파생 계산하므로 Amazon·BSR API 호출을 늘리지 않습니다. `[price-backfill]`은 공개 일봉·ECB 환율만 보강합니다.

자료 원문: [2025년 에이피알 사업보고서](https://apr-in.aprd.io/annual_report/%5B%EC%97%90%EC%9D%B4%ED%94%BC%EC%95%8C%5D%EC%82%AC%EC%97%85%EB%B3%B4%EA%B3%A0%EC%84%9C_2025%EB%85%84.pdf) · [APR IR](https://www.apr-in.com/ir.php). 기업분석 지표는 연구 목적이며 투자 권유가 아닙니다.


## KITA 선행운임 · APR 실적 민감도 (2026-11-09)

- **KITA RADIS 해상 참고운임**: 협력업체 조사 평균, USD/TEU·FEU. 공식 안내상 매월 첫째 주 업데이트됩니다. kita_rates.py가 매일 오전 07:30 정기 실행에서 공개 HTML을 무료 재검증하고 data/kita_rates.json에 누적합니다. HTTP 제한이나 표 구조 변경이 있으면 마지막 **출처 확인 스냅샷**을 보존하면서 접속 실패를 명시합니다. 2026-11-09 현재 공식 기본 조회 화면에서 확인된 노선은 **부산→롱비치 2026-01~10**뿐입니다. 다른 항로나 항공수출 운임을 미확인 상태에서 만들어 표시하지 않습니다.
- **관세청 해상수출 평균 운송비용**: 다음 달 중순 발표되는 신고수리일 기준 2TEU당 원화 평균 운송비용. KITA 단위, 표본, 시계열과 직접 연결하지 않습니다.
- **실적 민감도** 메뉴는 물류 탭과 분리되었습니다. 사용자가 확정 원가 분기를 선택하여 매출 증감, USD/EUR 매출 및 비용 환산 노출, 해상·항공·풀필먼트 비중과 단가, 비용 인식률, 광고비, 판매수수료율(%p), 매출원가 충격을 동시에 조절할 수 있습니다.
- 기준분기 및 재무 수치는 data/financials.json에서 가져옵니다. 운반비·광고·판매수수료·매출원가가 없는 **2026Q3 잠정실적은 모델 기준에서 제외**합니다. 분기 기여도·가정상 영업이익·영업이익률은 **1차 선형 민감도**이지 예측 또는 투자 조언이 아닙니다.
- 외화 노출·운송수단 배분·비용 인식 비중은 **회사 공식 공시가 없는 사용자 가정**으로 라벨을 붙입니다. 통화 노출과 운송비 배분 합계가 100%를 초과하면 계산을 보류합니다. 현지 풀필먼트는 독립 확인된 재무 계정이 아니므로 운반비의 가정상 내부 배분으로만 처리하여 중복 계상하지 않습니다.
- KITA 원문: https://www.kita.net/shippers/logisticsFare/logisticsSeaFare.do / 항공: https://www.kita.net/shippers/logisticsFare/logisticsAirFare.do
- 무료 오프라인 검사: python -m unittest tests/test_kita_rates.py -v 및 node tests/smoke_sensitivity.cjs

## KITA 미국 서안·동안 운임 / 기술적 바닥 형성 판별 (2026-11-09)

- 물류 탭의 KITA FEU 선행지표는 **미국 서안 부산→롱비치**와 **미국 동안 부산→뉴욕**을 같은 USD/40피트 기준으로 비교합니다. 서안의 주요 비교 항구는 LA·시애틀·오클랜드, 동안은 노퍽·서배너지만 모든 항구의 비용이 같다고 가정하지 않습니다.
- 서안은 KITA 공식 기본조회 페이지에서 2026년 1~10월을 직접 읽어왔습니다. 동안은 KITA 월간 공식 해상수출 공지에서 2026년 4·6·7월 값을 확인했으며, 2026년 9·10월은 KITA 운임을 인용한 별도 공개 운임 추적 서비스의 2차 값으로 **구분 표시**합니다. 동부의 미수집 8월, 9·10월 TEU는 공란으로 유지합니다.
- 매일 오전 공식 KITA 기본조회와 함께, 공식 뉴욕 운임 데이터가 부족한 동안에는 출처가 낮은 별도 운임 추적 서비스의 발표월을 무료로 모니터링합니다. 이 2차 인용값은 **절대 KITA 원문 직접 검증값이라고 표시하지 않습니다.** 데이터 소스 접근이 실패하면 검증 상태와 기존값을 함께 보존합니다.
- 바닥 판별 모듈 bottom_detector.py는 (i) 투매/평균거래량 급증, (ii) 3거래일 오른쪽 확인을 요구하는 스윙 저점과 RSI 상승 다이버전스/저점 재시험, (iii) MACD 히스토그램·RSI·5/20일선·전고점 돌파/거래량을 각각 확인합니다. 임의 가중치 0~10점은 **상승 확률이나 실증된 성공률이 아닙니다.**
- 바닥은 절대 '확정'이라고 판정하지 않으며 저점 재이탈 경계, 투매 후 반등 탐색, 바닥 형성 가능성, 추세 전환 1차 확인 등 근거 기반 단계로 표시합니다. 각 지표의 계산 기준일과 최근 저가·MA5·MA20·직전 10일 고가를 공개합니다. 미래 가격을 미리 읽거나 공시되지 않은 거시 정보를 결합하지 않습니다.
- 초기 분류 규칙은 과거 성과 백테스트가 완료된 투자 전략이 아닙니다. 거래비용·슬리피지·시장국면에 따라 효과가 달라질 수 있습니다.
- 참고: https://content.cmtassociation.org/a/spotting-a-market-bottom / https://help.stockcharts.com/scanning-and-alerts/scan-writing-resource-center/scanning-case-studies/scanning-for-divergences / https://www.fidelity.com/learning-center/trading-investing/technical-analysis/what-is-technical-analysis


## 에이피알 기관/외국인/연기금 수급 · 공매도/대차 (2026-11-09)

### 수급 탭과 판정 의미
- KRX 투자자별 거래실적(개별종목)에서 278470에 대해 개인·외국인(기타외국인 포함)·기관합계·연기금 등을 분리 수집합니다. **연기금은 기관합계의 구성원**이므로 외국인+기관과 별도로 더하지 않습니다. 연기금 매매동향과 국민연금의 공시 보유율도 서로 다른 정보입니다.
- 최근 5·20·60 **완전한 거래일**의 누적 순매수/순매도, 매수일 비율, 5일 매수세 가속도, 종가×거래량으로 근사한 거래대금 대비 순매수, 가격 추세·MA20·거래량을 종합해 각 주체의 수급을 연구용으로 구분합니다. 날짜 누락·KRX 접속 실패·거래소 범위 불일치가 있을 때는 판정 보류합니다. 참고 점수는 미래 성공확률이나 실제 수급 주체의 의도를 의미하지 않습니다.
- 외국인과 기관의 장단기 방향이 다르거나 주가가 하락하는데 외국인만 사는 상황을 무조건 좋은 수급으로 판정하지 않습니다. KRX와 NXT 포함 여부·시간외 거래 기준을 함께 살핍니다.
- 2026-11-09 **제3자 KRX 기반 5/20/60일 외부 요약**은 data/flow_reference.json에 별도 기록하며 공식 원자료와 섞지 않습니다.

### 공매도와 대차를 혼동하지 않기
- KRX 공매도 종합정보: 당일 거래대금/수량과 보고된 순보유잔고를 별도로 제시합니다. 순보유잔고는 T+2 보고 시차 및 정정 가능성이 있습니다. 거래비중을 종가×거래량으로 근사한 경우 공식 집계와 다를 수 있음을 표시합니다.
- 한국예탁결제원(KSD) 대차: 신규·상환·잔고(주)를 분리합니다. 대차잔고 증가는 신규 공매도의 확정 증거가 아니며 대차상환이 반드시 숏커버를 뜻하지 않습니다.
- 최종 투자자별 매매 정보는 오후 8시경 제공되므로 매일 저녁 20:30 KST에 수급을 재조회합니다. 오전 07:30 수집도 유지합니다.

### 무료 연결과 API 키
- KRX 종목별 투자자 실적과 공매도는 KRX 데이터정보시스템의 공개 화면을 pykrx 무료 클라이언트로 조회합니다. KRX의 공식 Open API 상품은 현재 종목별 투자자 수급·공매도 항목을 제공하지 않습니다. 공개 사이트 접속 제한으로 pykrx가 실패할 경우 이전 검증값과 오류 상태를 유지합니다.
- KSD 종목별 대차: 공공데이터포털의 **한국예탁결제원_증권대차서비스_GW** (https://www.data.go.kr/data/15157426/openapi.do) 활용신청 후, 발급받은 serviceKey를 GitHub 저장소 Settings > Secrets and variables > Actions > New repository secret에 **KSD_SLB_API_KEY** 이름으로 등록합니다. 키 원문은 공개 파일/채팅/화면에 적지 않습니다. 무료 개발계정 서비스이지만 **출처표시·상업적 이용금지** 조건이 있으므로 사이트 목적과 라이선스를 확인해야 합니다.
- KSD API 응답 항목명이 예상 스키마와 달라질 경우 해당 지표는 미확인으로 유지합니다. KSD API 키가 KRX 상세 연기금·외국인 수급을 대신하지는 않습니다.
- 수동 대안: imports/apr_investor_daily.csv, imports/apr_short_daily.csv, imports/apr_lending_daily.csv에 실제 확인한 날짜·원 단위 순매수·출처 URL을 기입합니다. 수동값은 별도로 출처 첨부 수동자료로 관리합니다.
- 구현: flows_collect.py / flows_engine.py / assets/flows.js / data/flows.json / tests/test_flows.py / tests/smoke_flows.cjs.

공식 원문: https://data.krx.co.kr/contents/MDC/MDI/outerLoader/index.cmd?screenId=MDCSTAT023 / https://data.krx.co.kr/contents/MDC/STAT/srt/MDCSTAT300.jsp / https://www.data.go.kr/data/15157426/openapi.do


### Kiwoom REST API 실측 수급 (KRX 공개화면 접근 제한 대체, 2026-11-09)

**KRX 공개 홈페이지에서 종목별 일간 수급은 GitHub Actions 실행 시 상세·기본 모두 0행으로 실패했습니다.** 실제 값을 자동으로 누적하려면 공식 증권사 데이터 API를 대안으로 사용할 수 있습니다.

1. [키움 REST API](https://openapi.kiwoom.com/m/guide/apiguide) 또는 [신청 페이지](https://openapi2.kiwoom.com/intro)에서 본인 키움 계좌로 REST API 서비스 신청 후 appkey와 secretkey 발급. 계좌 및 키 발급 조건은 증권사의 현행 안내를 따릅니다.
2. GitHub 저장소 Settings → Secrets and variables → Actions → New repository secret으로 **KIWOOM_APP_KEY**, **KIWOOM_SECRET_KEY** 두 개를 각각 등록. 절대 키를 코드·Issues·채팅이나 공개 JSON에 입력하지 않습니다.
3. GitHub Actions의 APR SIGNAL 기존 일일 예약(07:30 및 20:30 한국시간)이 일간 키움 **ka10059** 수급을 호출합니다. KRX 공개 pykrx와 Kiwoom API 중 실측이 확보된 값만 날짜별 합산해 5·20·60 거래일 수급을 판단합니다. 장내 주문/계좌/잔고/매수·매도 API를 전혀 사용하지 않습니다.
4. 키움 ka10059의 amt_qty_tp=1은 **금액**, trde_tp=0은 **순매수**, 투자자/연기금 금액은 **백만원** 단위이므로 원화 KRW로 ×1,000,000 변환합니다. 연기금은 기관합계에 포함됩니다. unit_tp=1은 수량 조회에 사용하는 구분으로 금액 변환과 혼동하지 않습니다. 누락/빈 문자열은 0으로 대체하지 않습니다. 페이지 일부만 수신되면 데이터 품질 경고를 보존합니다.
5. 이후 키움 API 수급과 KRX 투자자 분류, NXT 포함 여부를 대조해야 합니다. KSD 대차 실측은 키움과 별개의 무료 서비스키 **KSD_SLB_API_KEY** 등록 여부로 관리하며 계좌 데이터와 무관합니다.

- 구현: kiwoom_flows.py (au10001 읽기 전용 OAuth / ka10059 일별 투자자 수급) → flows_collect.py → data/flows.json → assets/flows.js.
- 검증: tests/test_kiwoom_flows.py의 인증·백만원→원 환산·연기금·페이지 연속조회·누락보존·토큰 비공개 단위검사.
- 공식 OAuth 명세: https://openapi.kiwoom.com/guide/apiguide?jobTpCode=07
- 공식 API 목록: https://openapi.kiwoom.com/m/guide/apiguide


### 공매도 거래·대차도 키움 REST 하나로 연결 (2026-11-09)
- 키움 REST appkey/secretkey를 Actions Secrets에 입력하면 수급 ka10059 외에 **ka10014 공매도 거래추이**와 **ka20068 종목별 대차 신규·상환·잔고**도 조회하도록 구성했습니다. 별도 KSD 키 없이 대차 실측부터 채울 수 있지만, KSD는 독립적인 공식 교차검증 데이터로 추가 활용할 수 있습니다.
- ka10014의 shrts_qty는 **당일 공매도 체결주수**, trde_qty는 **당일 전체 거래주수**입니다. 두 수량으로 계산한 공매도 거래비중은 **수량 비율**이며 공매도 거래대금 비중이나 공매도 순보유잔고가 아닙니다. 20거래일 기간 비중은 일간 백분율 단순 평균이 아니라 당일 공매도주수 합계 / 일간 전체 거래주수 합계로 계산하고, 반드시 해당 20거래일이 모두 확인될 때만 표시합니다.
- ka20068의 dbrt_trde_cntrcnt / dbrt_trde_rpy / rmnd는 각각 **대차 신규 체결주수 / 대차 상환주수 / 대차잔고주수**입니다. ka10014의 ovr_shrts_qty는 기간 누적 공매도 체결량이지 잔고가 아닙니다. 대차잔고와 공매도 순보유잔고는 별개이며 대차상환은 확정 숏커버가 아닙니다.
- 공매도 순보유잔고는 ka10014나 ka20068에 없으므로 KRX 신고 기반 개별 잔고 자료를 따로 수집하지 않는 한 미확인 상태로 둡니다. 두 API의 원본 금액 단위가 확정되지 않은 항목은 가격을 곱해 억지 금액을 만들지 않습니다. 미확인 수치는 0으로 채우지 않습니다.
- 개발·검증: kiwoom_short_lending.py 및 tests/test_kiwoom_short_lending.py. 원문: https://openapi.kiwoom.com/m/guide/apiguide


### PC·고정 IP·새 API 키 없는 APR 수급 조회 (2026-11-09)

- 새 기본 보조 출처는 네이버증권 로그인 없이 조회되는 공개 투자자 동향 화면입니다. naver_public_flows.py는 https://m.stock.naver.com/front-api/stock/domestic/trend?code=278470 에 기존 GitHub 예약에서 하루 2회만 소량 요청합니다. 실제 GitHub Actions 러너에서 2026-11-09 200/정상 JSON을 확인했고, 불투명 cursor로 2페이지 연속 조회도 검증했습니다. page=2, pageSize=60은 첫 10개만 되돌려주므로 자동화에 사용하지 않습니다.
- **KRX 장내** 외국인·기관·개인의 일별 순매수 **주수**를 가져옵니다. krx 객체만 사용하고 nxt 객체와 합산하지 않습니다. 이 공개 화면에는 연기금 종목별 내역이 없어 연기금을 공란으로 유지합니다.
- 수급 계산 엔진이 원화 순매수를 필요로 하므로 네이버 KRX 해당 일자의 **종가 × 순매수 주수**를 참고금액으로 저장합니다. 이 금액은 실제 투자자의 체결가격 가중 순매수 거래대금이 아닙니다. amount_estimated=true 및 KRW_ESTIMATED_NOT_ACTUAL로 구분되고 UI에 **≈**를 표시합니다. KRX 상세 또는 키움 실측 매매대금이 있을 때 네이버 근사치로 덮어쓰지 않습니다.
- 최대 9페이지, 90관측치로 제한하고 날짜·주수·거래량·매수량−매도량 일치를 검증합니다. 누락일·미발표 데이터·API 오류는 0으로 채우지 않고, 부분 수신은 부분 수신으로 표시합니다.
- 네이버 경로는 **공식 개발자 API가 아닌 공개 페이지 내부 읽기 전용 API**이므로 구조 변경·접근 제한 및 이용약관 확인이 중요합니다. 애드센스 미사용과 별개로 자료 재이용 조건을 존중합니다. 출처·기준일·KRX/NXT 범위 및 금액의 추정 여부를 표시합니다.
- 집 공인 IP 변경, 오라클 서버, PC 상시 가동 또는 추가 API 키는 필요 없습니다. 키움 REST가 정상 연결되면 별도로 수집 가능하며 해당 실측 금액을 우선합니다.
- 연기금·공매도 순보유잔고·대차 신규/상환/잔고는 이 네이버 투자자 동향에 없어 채우지 않습니다.

### 키움 키는 유지하되 GitHub 동적 IP에서 호출 중단 (2026-11-09)
키움 appkey/secretkey는 등록한 채로 두어도 됩니다. 다만 GitHub 호스팅 러너는 공인 IP가 가변이라 등록된 집 IP와 다릅니다. 연속 인증 실패/계정 보호를 피하기 위해 일반 GitHub 예약에서는 키움 OAuth/주문/조회 호출을 자동으로 생략하도록 했습니다. 네이버 공개 KRX 투자자 일별 주수 수집에는 키나 등록 IP가 필요 없습니다. 향후 별도 고정 IP 실행 환경을 구축하는 경우에만 KIWOOM_ALLOW_DYNAMIC_IP 환경값을 명시적으로 허용해 호출하도록 전환합니다(일반 GitHub에서는 권장하지 않음).


### APR 공매도 핵심 분석: KIS 일별 거래 + KRX 순보유잔고 (2026-11-10)

- **공매도 거래 자동 수집:** KIS 한국투자증권 OpenAPI FHPST04830000, GET /uapi/domestic-stock/v1/quotations/daily-short-sale. 주식코드 278470, 시장코드 J, 월단위 기간 조회. 응답 output2의 일자(stck_bsop_date), 공매도 체결수량(ssts_cntg_qty), 전체 거래량(acml_vol)을 검증해 공매도 주수 비율을 계산합니다.
- **KRX 공매도 순보유잔고:** KIS 위 API는 제공하지 않습니다. KRX Data Marketplace 공매도 순보유잔고(신고 시차·과소보고 가능성)만 별도로 확인합니다. 공매도 체결량 누적, 대차잔고, 대차상환을 순보유잔고라고 잘못 표현하지 않습니다.
- **KIS 계정 연결:** 한국투자증권 실제 계좌의 KIS Developers에서 앱키와 앱시크릿을 발급받아 GitHub Actions > Secrets > KI-S가 아니라 **KIS_APP_KEY**와 **KIS_APP_SECRET**으로 각각 등록합니다. 키 값은 공개 코드, 데이터 JSON, 채팅에 입력하지 않습니다. 단순 KIS 시장 데이터 API만 사용하며 계좌/주문 API는 호출하지 않습니다. 실제 거래 키 기준이고 모의투자 전용 API는 지원되지 않을 수 있습니다.
- 기존 GitHub 오전 07:30·저녁 20:30 수집에 연결되므로 집 PC, 별도 서버, 키움 고정 IP는 사용하지 않습니다. 계정 조건·실제 접근 권한은 등록 뒤 Runner에서 확인해야 합니다. KIS 키가 없거나 실패하면 이전 검증 데이터를 유지하면서 실패 상태를 표시합니다.
- **금융위원회 주식대차정보 별도 API:** 사용자가 신청한 공공데이터포털 서비스키는 GitHub secret FSC_STOCK_LENDING_API_KEY 이름으로 넣어야 하며, KIS 공매도 API와는 서로 다른 데이터입니다. 현재 금융위 공식 서비스 Base URL은 https://apis.data.go.kr/1160100/GetStocLendBorrInfoService_V2 (포털 카탈로그 15059612). 공식 Swagger에서 종목별 조회 경로 getStItemLendAndBorrStatu_V2, 필터 isinCdNm, 대차체결주수/상환주수/잔여주식수 필드를 검증해 별도 수집을 연결했습니다. 다만 첫 Live 테스트는 403으로 키 활성화 또는 API 이용권한 확인이 필요합니다. 인증 실패 시 실제 대차잔고가 0이라고 표시하지 않습니다. KSD_SLB_API_KEY는 KSD 별도 API에 사용하는 다른 Secret입니다.
- KSD·금융위 주식대차 API 자료는 공공누리 2유형(출처표시 + 비상업적 이용)이며 광고가 없는 사이트에서도 원천 출처표시와 다른 이용 조건을 따라야 합니다.
- 테스트: tests/test_kis_short_sales.py. 5·20일 공매도 거래비중은 단기 압력 판단에 사용하되, 포지션 감소나 숏커버 확정이라고 표시하지 않습니다.


#### 금융위원회 대차 API 연결 검증 및 상태
- Source: https://www.data.go.kr/data/15059612/openapi.do
- Swagger Base URL: https://apis.data.go.kr/1160100/GetStocLendBorrInfoService_V2
- Operation: GET /getStItemLendAndBorrStatu_V2
- Required serviceKey, numOfRows, pageNo, resultType. Optional basDt, isinCdNm.
- APR identifies ISIN KR7278470000 and name 에이피알. Source fields: lnbCclStckCnt (대차체결주수), lnbRdptStckCnt (상환주수), lnbRmanStckCnt (잔여주식수). No inference of net short positions.
- Daily FSC update occurs next business day after 13:00 KST. Existing GitHub Actions 16:00 KST runs only FSC update and keeps morning/evening free flow refresh.
- GitHub Actions test with registered FSC_STOCK_LENDING_API_KEY returned HTTP 403 on 2026-11-10 KST. FSC FAQ: verify approval/serviceKey or recheck after short activation interval; no key value exposed. The collector stops after the first 403, retains verified historical values, and reports authorization_denied.


### 2026-11 valuation audit

- PER/PBR bands use primary-verified parent-attributable **basic** TTM EPS / treasury-excluded BPS, not diluted multiples. Fixed multiples are scenario lines, not historical percentiles.
- Verified valuation inputs now live in `config/apr_verified_valuation.json`, independently transcribed from official APR reports (2024 FY through 2025 FY) and DART 2026 Q1/H1. URLs, PDF page locations / DART sections, snapshot hashes, disclosure dates and underlying won/share-day values are retained. Rounded dashboard quarterly figures and automated DART refreshes do not overwrite these anchors.
- `verified_valuation.py` reconstructs **basic** TTM EPS using parent-attributable profit and exact weighted outstanding common share-days: FY − prior YTD + current YTD, divided by trailing calendar days. It is not end-share EPS, a sum of rounded EPS, or a diluted consensus estimate. Each report's basic/diluted cumulative EPS is shown separately. BPS uses parent equity / (period-end issued common shares − treasury shares).
- Availability is the day **after** the verified filing date, conservatively avoiding unknown intraday/after-close release timing. This is not a claim to the earliest earnings announcement. The 2024 FY report is dated 2025-03-21 and the 2025 FY report 2026-03-23. Historical 5:1 split-adjusted figures are not adjusted twice. Treasury cancellations are not subtracted twice from already treasury-excluded shares.
- The 2024 H1 comparative EPS note uses 181 days versus 182 calendar days. We do not silently repair it. The 2025 H1 TTM PER event is excluded, with a blank band until the next verified event; BPS remains usable. A new excluded/nonpositive EPS cannot silently fall back to an older profitable period. 2026 Q3 preliminary profit is not mixed into verified EPS; the latest anchor remains 2026 H1 (TTM basic EPS 11,545.69 won; reported H1 basic EPS 6,913 won).
- `valuation_audit.py` separately compares saved OpenDART consolidated profit/equity amounts against the operating financial table. Its match/mismatch is not the verification status of the independently sourced parent-attributable EPS/BPS inputs.
- Forward PER calculator supports user-supplied expected EPS, expected attributable profit / forecast weighted-average shares, or a clearly labeled TTM growth sensitivity. No analyst consensus is fabricated. NTM and FY+1 are user-selected horizons, and nonpositive earnings produce no PER.
- Run `python -m unittest discover -s tests -v`, `python build_research_data.py`, all `tests/smoke_*.cjs`, and JavaScript syntax checks.
