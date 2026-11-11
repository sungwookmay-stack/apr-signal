# 시나리오 일일 기록

`scenario_monitor.update(data_dir, now=None)`를 재무 데이터 생성 뒤 호출한다. 네트워크 호출, 유료 API, 주문은 없다. KST 날짜별 한 행을 `data/scenario_monitor.json`에 저장한다. 같은 날 내용이 바뀌면 이전 평가를 `revisions`에 보존한다. 동일 내용 재실행은 행을 늘리지 않는다. 과거 날짜의 재구축·역순 관측은 거절한다. 기존 CI 동시 실행 직렬화와 함께 사용한다.

## 두 종류 판정

- 전체 `classification`: 사용자 사진의 미래 가설. 4조건 모두 직접 검증된 유일 시나리오만 분류. 그 외 `pending`. 2026년 말/FY26 조건은 12월31일 종료 전, 2027 조건은 연도 시작 전 확정하지 않는다. 최소 날짜 도달은 실제 실현을 의미하지 않는다.
- `provisional`: 현재 공식 자료에서 각 가설의 **구성요소**에 해당하는 부분지지 조건을 중복 없이 센다. 최소 2조건·유일 우세·직접 반증 없음이면 `Bull 쪽 참고 신호` 등 표시. 이 문턱은 사진에 없으며 명시적인 모델 가정이다. 데이터가 많이 공개된 부문에 편향되고 집계 방법에 민감하다. 확률/투자추천이 아니다. 미래 전체 판정은 계속 보류 가능하다.
- 부분지지와 전체 확인은 별개다. 예컨대 Costco 입점은 확장 구성요소만 지지하며 재주문·판매량·Amazon/Ulta 잠식 제한을 입증하지 않는다.

## 데이터와 공개 시점

- 사용자 이미지의 12개 정성 조건을 `config/scenario_criteria.json`에 전사했다. 수치 목표·확률·임계값은 원문에 없다.
- 공식 IR 3Q26, APR 공식 Costco/Walmart/Shoppers 발표, HSA Singapore 발표를 원문 검증 후 참고 자료로 연결했다. 신규 공식 자료는 `known_at` 최초 확인 시각 이후만 사용한다. HSA는 일부 배치 회수와 비영향 배치 판매재개·검사조건이며 APR 전체 판매금지 지속의 근거가 아니다.
- 기존 재무는 실제 공시일·분기말·원문/수신번호 확인 후 참고로 사용한다. 영업이익률은 영업이익/매출이다. CFO는 별도 감사 중이어서 사용하지 않는다. 누적 합산은 모든 분기의 `accounting_basis`가 명시되고 같은 경우에만 허용한다. IFRS18 재작성과 종전 기준을 섞지 않는다.
- 날짜만 있는 공개일은 해당 KST 날짜 종료 후 사용한다. 누락 날짜·미래 자료는 제외. `history`는 실행 당시 실제 저장한 평가이며 과거 모의실적이 아니다.
- Ulta 카탈로그는 proxy다. POS/재주문/매출로 환산하지 않는다.

## 후속 직접 근거 입력

검토를 거친 `data/scenario_evidence.json`의 `evidence` 배열을 지원한다. 각 항목은 `condition_id`, `review_status: verified`, `evidence_type: direct`, `covers_entire_condition: true`, `stance: supported|contradicted`, `source_url`(공식 HTTPS), `quote`, `reason`, `published_at`, `known_at`, `observed_at`, `period_end`를 요구한다. 원문을 검토하지 않은 검색결과/뉴스로 생성하면 안 된다. 상충 직접 증거는 conflicting으로 보류한다. 기간이 사진의 미래 가설 시작보다 이전이면 전체 근거로 채택하지 않는다.

## 스키마

최상위 `schema_version`, `updated_at_utc`, `methodology`, `latest`, `history`.
평가행 `date`, `evaluated_at_utc`, `classification`, `label`, `reason`, `provisional`, `scenarios`, `context`, `missing`, `fingerprint`, `revisions`.
조건 `status`, `reason`, `evidence`, `partial_evidence`, `missing`.
참고 fact `id`, `label`, `value`, `unit`, `period`, `asof`, `available_from`, `known_at`(신규 원문 보완), `source`, `source_url`, `evidence_type`, `note`, `condition_ids`, `partial_support`(해당시).

브라우저 조회만으로 서버 Git 기록을 쓸 수 없다. 서버 일일 기록과 브라우저 조회 시점은 구분해서 표시한다. 웹 페이지는 기록된 자료 기준일을 숨기지 않는다.

## 최신성 및 자동 갱신 한계

공식 보완 원문(`verified_context`)은 이번에 사람이 원문 검토한 고정 기록이며 신규 IR·보도자료·HSA 공지를 자동 크롤링하는 기능은 아니다. 자동 갱신되는 재무자료가 있어도 과거 보완자료의 결론을 새 실적으로 추정하지 않는다. 과거 사건은 context에 보존하되 **기준일 120일 초과**인 부분지지 근거는 참고 방향 집계에서 제외한다. 120일은 투자/통계적 근거가 아닌 공개된 운영 모델 가정이다. 더 최신 분기의 공개 재무근거가 있으면 이전 분기 자료의 부분지지 집계도 제외한다. `signal_eligible` 및 `signal_exclusion_reason`으로 확인할 수 있다. 새 원문을 검토·추가하지 않으면 참고 방향은 자동으로 보류될 수 있다. 어느 시나리오든 직접 증거 충돌이 존재하면 임시 참고 방향도 보류한다.
