# 서비스 고도화 로드맵

## 1. 지금 코드베이스에서 바로 효과가 큰 항목

### A. 데일리 리포트 평가 하네스

- 적용 위치: `scripts/evaluate_daily_report.py`, `report_eval.py`, `docs/evals/`
- 적용 방식:
  - 생성된 `docs/archive/YYYY-MM-DD.html`
  - 재현 가능한 `docs/replay/YYYY-MM-DD.snapshot.json`
  - 리콜/필터 로그(`debug.collections`, `debug.filter_rejects`)
  를 함께 읽어서 품질을 점수화한다.
- 개선 효과:
  - 리포트 품질을 감으로 보지 않고 수치로 추적 가능
  - 브리핑 카드 수, 섹션 충실도, 중복도, 최신성, 요약 품질을 매일 비교 가능
  - 다음 실행의 요약 프롬프트에 자동 피드백 반영 가능

### B. OpenAI 요약 프롬프트 자동 피드백 루프

- 적용 위치: `main.py`, `docs/evals/latest-feedback.txt`
- 적용 방식:
  - 전날 평가 결과에서 요약 품질 관련 피드백만 추출
  - 다음 날 기사 요약 프롬프트에 자동으로 붙인다
- 개선 효과:
  - 수치 누락, 비슷한 문장 시작 반복, 두루뭉술한 요약을 점진적으로 줄일 수 있음
  - 코드 수정 없이도 요약 품질을 매일 보정 가능

### C. 운영 지표를 Admin Dashboard에 연결

- 적용 위치: `docs/admin/`, `docs/evals/history.json`
- 적용 방식:
  - 현재 GA4/운영 대시보드와 별도로 평가 점수 추이 그래프 추가
  - `overall_score`, `freshness`, `summary_quality`, `diversity`를 시계열로 노출
- 개선 효과:
  - "오늘 리포트가 왜 좋았는지/나빴는지"를 운영자가 바로 이해 가능
  - 배포 후 품질 저하를 빠르게 감지 가능

## 2. 이 리포에 추천하는 Codex 플러그인 / 스킬

### GitHub 플러그인

- 추천 스킬:
  - `github:gh-fix-ci`
  - `github:gh-address-comments`
  - `github:yeet`
- 적용 포인트:
  - 평가 하네스가 경고를 낼 때 CI 로그/리뷰 댓글을 바로 따라가며 수정
  - dev 검증 결과를 PR 단계에서 빠르게 정리
- 기대 효과:
  - 운영 코드 수정 속도 향상
  - 회귀 발생 시 원인 파악 시간 단축

### Hugging Face 플러그인

- 추천 스킬:
  - `hugging-face:huggingface-community-evals`
  - `hugging-face:huggingface-datasets`
- 적용 포인트:
  - 일자별 리포트/스냅샷을 평가 데이터셋처럼 관리
  - semantic rerank 실험 전후 품질 비교 자동화
- 기대 효과:
  - rule 기반 랭킹과 semantic rerank의 실효성 검증
  - 장기적으로 품목/섹션별 약한 구간 식별

### Build Web Apps 플러그인

- 추천 스킬:
  - `build-web-apps:web-design-guidelines`
  - `build-web-apps:react-best-practices`
- 적용 포인트:
  - 현재 정적 admin/dashboard를 점진적으로 개선할 때 활용
  - 평가 결과, 검색 성능, 클릭 데이터를 시각적으로 재구성
- 기대 효과:
  - 운영자가 품질 저하를 더 빨리 읽을 수 있음
  - 분석 화면의 해석 비용 감소

## 3. 추천 외부 GitHub 레포 / 도구

### Promptfoo

- 링크:
  - https://github.com/promptfoo/promptfoo
  - https://www.promptfoo.dev/docs/configuration/guide/
- 추천 이유:
  - YAML 기반으로 테스트 케이스와 assertion을 정의하기 쉬움
  - CI에 붙이기 편함
- 이 리포 적용 예:
  - "정책 섹션 요약은 수치를 1개 이상 포함해야 한다"
  - "동일 이벤트 중복 요약은 fail"
  - "요약 길이 범위 유지" 같은 규칙형 eval
- 기대 효과:
  - 하네스를 더 선언적으로 관리 가능
  - 프롬프트/모델 변경 A/B 비교가 쉬워짐

### Langfuse

- 링크:
  - https://github.com/langfuse/langfuse
  - https://langfuse.com/docs
- 추천 이유:
  - tracing, prompt versioning, eval, experiment를 한데 묶어 관리 가능
- 이 리포 적용 예:
  - 날짜별 요약 생성 trace 저장
  - 어떤 피드백 버전의 프롬프트가 점수를 올렸는지 비교
- 기대 효과:
  - "왜 오늘 점수가 떨어졌는가"를 프롬프트/모델/입력 단위로 분해 가능

### Inspect

- 링크:
  - https://inspect.aisi.org.uk/
- 추천 이유:
  - 평가 하네스를 코드형으로 정교하게 작성하기 좋음
- 이 리포 적용 예:
  - 일자별 snapshot을 dataset으로 읽고 섹션 완결성/신선도/중복도 scorer 구성
  - summary prompt 후보 여러 개를 오프라인 실험
- 기대 효과:
  - rule + model-graded eval을 함께 설계하기 좋음
  - 장기 실험용 하네스로 확장하기 쉬움

### DeepEval

- 링크:
  - https://github.com/confident-ai/deepeval
- 추천 이유:
  - LLM 평가 메트릭을 빠르게 붙일 수 있음
- 이 리포 적용 예:
  - 요약 사실성, 관련성, 간결성 같은 judge 기반 점수 보조
- 기대 효과:
  - 현재 rule-based 하네스에 judge 계열 지표를 얹기 쉬움

## 4. 추천 적용 순서

1. 현재 구현한 내부 하네스를 daily/dev 검증에 먼저 고정한다.
2. `docs/evals/history.json` 점수 추이를 2주 정도 쌓는다.
3. 점수가 자주 흔들리는 축만 골라 Promptfoo 또는 Inspect 실험 세트를 만든다.
4. Langfuse를 붙여 프롬프트 버전과 점수 상관관계를 기록한다.
5. semantic rerank, query seed, summary prompt를 각각 분리 실험한다.

## 5. 핵심 판단

이 서비스는 이미 수집, 랭킹, 리플레이, dev 검증 기반이 갖춰져 있다. 그래서 가장 큰 레버리지는 "새 모델 추가"보다 "평가 하네스와 피드백 루프를 운영 파이프라인에 붙이는 것"이다. 먼저 점수와 힌트를 안정적으로 쌓아야, 그 다음 semantic rerank나 LLM judge 도입도 비용 대비 효과가 분명해진다.
