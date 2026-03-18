# 2026 Q1 Debug Sample Analysis

## Scope

- Analysis window: January 2026 to March 2026
- Sample method: fixed-seed random sampling from Q1 debug archives, then regeneration on `dev` with the updated classifier
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

## Regeneration Method

Local execution still did not contain live collection credentials such as `NAVER_CLIENT_ID` and `NAVER_CLIENT_SECRET`, so the 10 sampled dates were regenerated through GitHub Actions `dev-verify.yml` on branch `dev`, which can use repository secrets and emit fresh debug reports to `codex/dev-preview`.

Completed reruns:

- `2026-01-07`: [23191475830](https://github.com/NH-Horti/agri-news-brief/actions/runs/23191475830)
- `2026-01-20`: [23191956739](https://github.com/NH-Horti/agri-news-brief/actions/runs/23191956739)
- `2026-01-23`: [23192360220](https://github.com/NH-Horti/agri-news-brief/actions/runs/23192360220)
- `2026-01-29`: [23192790478](https://github.com/NH-Horti/agri-news-brief/actions/runs/23192790478)
- `2026-02-03`: [23193296366](https://github.com/NH-Horti/agri-news-brief/actions/runs/23193296366)
- `2026-02-20`: [23194139310](https://github.com/NH-Horti/agri-news-brief/actions/runs/23194139310)
- `2026-02-25`: [23194674690](https://github.com/NH-Horti/agri-news-brief/actions/runs/23194674690)
- `2026-03-09`: [23195160178](https://github.com/NH-Horti/agri-news-brief/actions/runs/23195160178)
- `2026-03-10`: [23195677485](https://github.com/NH-Horti/agri-news-brief/actions/runs/23195677485)
- `2026-03-11`: [23196295428](https://github.com/NH-Horti/agri-news-brief/actions/runs/23196295428)

This removed the earlier observability gap and let the second pass use fresh metadata such as `selection_stage`, `selection_note`, `origin_section`, `reassigned_from`, `source_query`, and `selection_fit_score`.

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

## Second-Pass Findings From Regenerated Reports

Fresh regenerated reports surfaced a tighter set of residual errors:

- `dist` still admitted political market-visit stories where `가락시장/도매시장` was only the venue, not the operational subject.
- `supply` and `policy` still leaked livestock-dominant stories when the headline had no real horticulture anchor.
- `supply` still admitted training / recruitment / organization-admin stories such as `농업대학 신입생 모집` and simple org rename pieces.
- `policy` still admitted generic forestry-response and local budget-drive administration stories.
- `pest` still had a tail risk of admitting agro-input marketing / labeling stories that mention `농약` but are not actual pest-control execution.
- `supply` still slightly under-ranked explicit multi-commodity outlook summaries such as storage-vs-facility vegetable price trend articles.

## Second-Pass Improvements Applied

### Noise Rejection

- Added `market political visit` rejection for stories where politicians merely visit wholesale markets and discuss general politics.
- Added title-focused livestock dominance rejection for `supply` and `policy`.
- Added `agri training / recruitment` rejection for `농업대학`, `신입생 모집`, `교육생 모집` style stories.
- Added `agri org rename` rejection for simple organization rename/admin stories in `supply`.
- Added `policy forest admin` rejection for `산불/산림/임업` administrative stories without clear horticulture anchors.
- Added `policy budget drive` rejection for `국가투자예산 확보`, `전략사업 발굴` style local administration stories.
- Added `pest input marketing noise` rejection for fertilizer / ad-labeling stories that only look pest-related because of `농약` wording.

### Dist Prioritization

- Tightened `dist` macro-export noise logic so generic `K-푸드 / 비관세장벽 / 전쟁 여파` headlines no longer survive on generic agriculture vocabulary alone.
- Added rejection for local crop-strategy / smart-agri designation stories that are planning-stage or crop-promotion stories rather than market-operation stories.
- Preserved ownership of strong `dist` stories during global section reassign so market-disruption / market-ops / supply-center / sales-channel stories do not drift back into `supply`.

### Supply Recall / Ranking

- Added explicit `supply price outlook` recognition for multi-commodity price/trend summaries, including storage-vs-facility vegetable outlook stories.
- Applied relaxed-headline gating to `supply_feature_backfill` so interview/profile stories cannot slip in during tail backfill.

## Remaining Gaps

- `policy` still underfills more than other sections in the regenerated sample. More recall expansion is still likely needed around local government market-structure policy and actionable regional programs.
- `supply` still has borderline threshold misses on compact market outlook stories; another pass can tune the margin between feature tails and direct outlook summaries.
- `pest` can still surface near-duplicate local execution stories when the pool is shallow, so the next pass should tighten same-story diversity on regional pest coverage.
- A full second 10-day rerun after the very latest macro-export follow-up patch is still optional. The final pass below reran the two dates that contained the active residual errors and confirmed the fixes on live debug output.

## Final Representative Rerun Verification

After the final follow-up patch (`acae12e`, `Tighten macro export dist filtering`), representative dates with active residual errors were regenerated again on GitHub Actions:

- `2026-02-20`: [run 23218703861](https://github.com/NH-Horti/agri-news-brief/actions/runs/23218703861)
  - `build_tag=acae12e`
  - removed false-positive `K-푸드 수출 1000억 달러 시대의 열쇠, '비관세장벽 4단계 대응 체계'에 있다`
  - `dist` kept only the operational stories:
    - `농협개혁· 온라인도매시장 법제화 국회 통과`
    - `“농가 포장·운송비 부담 완화”…한국청과, 보전금 첫 지급`
- `2026-03-11`: [run 23219138903](https://github.com/NH-Horti/agri-news-brief/actions/runs/23219138903)
  - `build_tag=acae12e`
  - removed false-positive `“농약인 줄”…‘비료’ 온라인 허위·과대광고에 농가 혼란`
  - `pest` kept only execution-style stories such as:
    - `과수화상병 예방 방제약제 공급`
    - `돌발 해충 월동난 예찰 실시`
    - `복숭아 재배농가 월동 병해충 방제 현장지도 강화`

## Validation

Applied code and tests were validated with:

- `.\.venv\Scripts\python.exe -m unittest tests.test_classifier_behavior`
- `.\.venv\Scripts\python.exe -m unittest tests.test_regressions`
- `.\.venv\Scripts\python.exe -m unittest tests.test_commodity_board`

All passed after the second-pass changes in this pass.
