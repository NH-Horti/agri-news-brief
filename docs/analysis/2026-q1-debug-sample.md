# 2026 Q1 Debug Sample Analysis

## Scope

- Analysis window: January 2026 to March 2026
- Sample method: fixed-seed random sampling from existing `docs/debug/*.json`
- Seed: `20260317`
- Sample dates:
  - `2026-01-07`
  - `2026-01-20`
  - `2026-01-23`
  - `2026-01-29`
  - `2026-02-03`
  - `2026-02-20`
  - `2026-02-25`
  - `2026-03-09`
  - `2026-03-10`
  - `2026-03-11`

## Why Existing Debug Reports Were Used

Local execution environment did not contain live collection credentials such as `NAVER_CLIENT_ID`, `NAVER_CLIENT_SECRET`, or GitHub deployment secrets. For this pass, analysis was performed on the already archived debug reports in `docs/debug/`, which still provided enough breadth to detect persistent scoring and filtering patterns without user-picked article bias.

## Aggregate Signals From The 10-Day Sample

| Section | Avg `items_total` | Avg selected | Underfill days | Dominant reject signals |
| --- | ---: | ---: | ---: | --- |
| `supply` | 23.9 | 2.5 | 9/10 | `below_threshold` |
| `policy` | 18.3 | 1.4 | 10/10 | `below_threshold`, `source_cap`, `headline_gate` |
| `dist` | 11.1 | 4.0 | 3/9 | `below_threshold`, `similar_story`, `headline_gate` |
| `pest` | 8.6 | 2.2 | 5/5 | `below_threshold` |

Interpretation:

- `policy` is the weakest section in recall-to-selection conversion. It underfills every sampled day.
- `supply` has decent raw collection volume, but too many useful stories still die at threshold.
- `dist` is less of a volume problem than a type-ranking problem: weak or ambiguous export stories compete with true market-operation stories.
- `pest` is mainly a small-pool problem. Execution stories were present but often scored like tail items.

## Main False-Negative Patterns

### 1. Local price-support policy stories were systematically under-scored

Representative misses from sampled reports:

- `2026-01-20`: `양구군 농산물 최저 가격 지원금 4억원 지급`
- `2026-01-20`: `양구군, 농산물 최저 가격 지원…9개 품목 4억원`
- `2026-01-20`: `양구군 '2025년 농산물 최저 가격 지원' 사업을 통해 4억여 원 지급`

Observed issue:

- These were falling as `policy / below_threshold` even though they are highly aligned with the brief’s real use case.
- The previous logic recognized central-government policy and broad market briefs better than local government price-support execution.

### 2. Small-pool pest execution stories were not protected enough

Representative sampled pattern:

- fire blight / tomato leaf miner execution stories in low-volume days were present, but selected too inconsistently relative to generic disease roundups.

Observed issue:

- `pest` had low candidate counts, but the threshold and final-selection path still behaved like a normal high-volume day.
- Underfill logic was not sufficiently biased toward actual execution stories such as `예찰`, `약제`, `방제 계획`, `전수조사`.

### 3. Dist market-action and field-operation stories were mixed with generic export headlines

Representative sampled misses and weak handling:

- `농산물 유통 거점`, `직거래`, `공동구매`, `푸드통합지원센터`, `수출 선적`, `판로 확대` type stories often lived too close to the threshold.
- Actual operation stories could lose position to generic `K-푸드` export headlines.

Observed issue:

- The old rules had a gap between strong wholesale/APC anchors and softer distribution-channel actions.
- A useful operational type existed in debug data, but it was not first-class in the `dist` scorer.

## Main False-Positive Patterns

### 1. Generic macro export / campaign / promo stories polluted `dist`

Observed recurring noise families:

- broad `K-푸드` export macro headlines
- campaign-style stories such as anti-artificial-flower campaigns
- local-coop promo/profile stories such as `작지만 강한 농협`

Problem:

- These stories carry surface-level distribution vocabulary, but they do not help a market-operation brief.
- Without a stricter distinction, they compete with true field-operation items.

### 2. Policy section accepted weak macro or headline-only stories

Representative selected examples from sampled reports:

- `2026-02-20`: `설 이후 가격 하락 공식 약화…사과·배 ‘버티기’ 반복`
- `2026-02-25`: `농식품부 수급 점검... "채소·과일 전반 안정…체감 물가 관리 강화"`
- `2026-03-09`: `2월 농축산물 소비자물가 1.4%↑…“쌀·사과 공급 안정 노력”`
- `2026-03-10`: `정부 “농축산물 가격 대체로 하락…수급 관리 강화”`

Problem:

- These are not always outright wrong, but the old `policy` ranker over-favored broad management headlines relative to local actionable policy and program execution.

## Improvements Applied In This Pass

### Policy

- Added explicit `지자체 농산물 가격안정 / 최저가격 지원` context recognition.
- Relaxed small-pool dynamic thresholds for `policy`.
- Lowered underfill cut for local price-support policy stories.
- Expanded policy recall queries with:
  - `농산물 가격안정 지원`
  - `농산물 최저가격 지원`
  - `농산물 가격안정 지원사업`

### Dist

- Added dedicated recognition for `원스톱 수출지원 허브 / 애로 해결` operational export-support stories.
- Blocked those stories from being misclassified as generic macro export noise.
- Added stronger rejection for:
  - macro `K-푸드` export noise
  - campaign noise
  - local coop promo/profile tails
- Added precedence rule so hub-style export-support stories do not displace stronger online-wholesale / market-ops stories when both exist.

### Pest

- Relaxed small-pool threshold behavior for execution-style pest stories.
- Lowered underfill cut for `방제 계획 / 약제 지원 / 전수조사` type execution stories.
- Expanded pest recall queries with:
  - `과수화상병 방제 계획`
  - `과수화상병 약제 공급`
  - `토마토뿔나방 약제 지원`
  - `토마토뿔나방 전수조사`

### Selection / Debug Traceability

- Strengthened `forced_section` preservation so forced pest items survive final slice and dedupe.
- Added richer debug metadata already introduced in this branch:
  - `selection_stage`
  - `selection_note`
  - `selection_fit_score`
  - `origin_section`
  - `reassigned_from`
  - `source_query`
  - `source_channel`

## Remaining Gaps

- `policy` still underfills heavily in the sampled archive. More recall expansion is still likely needed around local government program reporting and market-structure policy.
- `supply` still loses many articles to `below_threshold`; this needs a second pass focused on feature-quality vs macro-noise separation.
- Archived debug reports before this patch do not contain the newer metadata fields, so historical comparisons still have observability limits.

## Validation

Applied code and tests were validated with:

- `.\.venv\Scripts\python.exe -m unittest tests.test_classifier_behavior`
- `.\.venv\Scripts\python.exe -m unittest tests.test_regressions`
- `.\.venv\Scripts\python.exe -m unittest tests.test_commodity_board`

All passed after the changes in this pass.
