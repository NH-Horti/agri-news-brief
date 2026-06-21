## Daily Eval (2026-06-15)
- Overall: **93.27** (pass)
- Operational: **95.02**
- Reader quality: **94.27** (capped; penalty=0.8, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **93.27** (needs_iteration, editorial_below_target_bounded_penalty; editorial=85.0, operational=95.0)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=92.3, retrieval=86.9, section_fit=96.9, core=99.2, commodity=88.0
- Briefing cards: 19 / Commodity cards: 20
- Sections: supply:5/5 raw=254, policy:4/5 raw=123, dist:5/5 raw=51, pest:5/5 raw=38
- Metrics: title_unique=1.00, domain_diversity=0.79, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=4.00, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=9, commodity_active_today=15, commodity_active_today_unlinked=6, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.78, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **85.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=84.0, section_fit=86.0, core=83.0, summary=72.0, missed=81.0, noise=80.0
- Summary: 전반적으로 읽을 만한 브리핑이지만, 공급·유통·병해충 섹션에 지역 출하/피처성 꼬리 기사와 중복감 있는 선택이 섞였고, 정책은 원시 후보가 충분한데도 4건에 그쳤습니다. 핵심 기사 몇 개는 적절하지만, 더 강한 전국 단위 후보를 두고 약한 로컬·해설성 기사로 채운 흔적이 있어 90점대 중후반 평가는 어렵습니다.
- [medium] underfill: 정책 섹션 4건만 선정 - 원시 후보가 충분한데 5건을 채우지 못함.
- [high] wrong_priority: 요코하마도매시장 '소매 분산 물류'로 특화 - 일본 도매시장 기사와 주제 중복도가 높아 독립 카드 가치가 약함.
- [high] filler: [픽! 영동] 금강 모래밭서 생산된 '양산수박' 출하 - 전형적 지역 출하 소식으로 전국 수급 의미가 약함.
- [medium] filler: "보이면 바로 사세요"…6월 지나면 사라지는 '초여름 과일' - 리테일 피처 성격이 강하고 수급 이슈 밀도가 낮음.
- [high] missed_better_candidate: 온라인도매시장 실적은 '기망' 미선정 - 유통 구조·시장 운영 문제를 다룬 더 직접적인 국내 기사였다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
