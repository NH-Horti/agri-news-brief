## Daily Eval (2026-06-09)
- Overall: **96.61** (pass)
- Operational: **96.61**
- Quality gate: **96.61** (target_met, all_targets_met; editorial=95.0, operational=96.6)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=100.0, core=100.0, commodity=100.0
- Briefing cards: 19 / Commodity cards: 39
- Sections: supply:4/5 raw=168, policy:5/5 raw=115, dist:5/5 raw=37, pest:5/5 raw=35
- Metrics: title_unique=1.00, domain_diversity=1.00, summary_presence=1.00, summary_numeric=0.79, fresh_72h=1.00, fit_avg=4.29, false_positive=0.00, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Section count gate: 98.0 (soft_fallback)
- Score calibration: 83.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=80.0, section_fit=78.0, core=76.0, summary=88.0, missed=79.0, noise=77.0
- Summary: 핵심 이슈 자체는 여름철 수급안정, 비료값 지원, 화상병 확산 등으로 대체로 맞췄지만, 정책·유통 섹션에서 약한 기사와 중복성 높은 기사 비중이 크다. 특히 정책 섹션의 ‘특별성과 포상’은 독자 효용이 낮은 내부 인사성 기사인데 코어로 잡은 점이 가장 큰 감점 요인이다. 유통은 운영·물류 기사보다 로컬 판촉성 특판이 과하고, 공급은 후보 풀이 충분한데도 4건만 채워 underfill 상태다. 요약은 대체로 읽히지만, 더 강한 후보를 두고 약한 카드가 들어간 편집 판단이 아쉽다.
- [high] weak_core: 농식품부 , 특별성과에 파격 포상 - 부처 내부 포상 소식으로 정책 효용이 낮다.
- [high] duplicate: [관망경]칭찬은 공무원도 춤추게 한다 - 같은 포상 이슈의 해설성 중복이다.
- [medium] duplicate: 특별 성과 낸 공무원에 파격 보상…농식품부, 11명에 포상금 등 수여 - 포상 기사 3건 반복으로 지면 낭비다.
- [medium] wrong_priority: 30% 할인에 무료배송까지…곡성 멜론 특별전 - 지역 판촉행사로 유통 운영기사보다 우선순위가 낮다.
- [medium] wrong_priority: 함양군·함양농협, 양파 수급 안정 위한 소비 촉진 총력 - 로컬 특판 성격이 강해 전국 유통면 핵심성과 약하다.

### Improvement Hints
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
