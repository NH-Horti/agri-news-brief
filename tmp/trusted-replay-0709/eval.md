## Daily Eval (2026-07-09)
- Overall: **84.00** (warn)
- Operational: **91.88**
- Reader quality: **84.00** (capped; penalty=6.8, cap=84.0, reasons=commodity_false_link, commodity_false_link_severe, preferred_slot_underfill)
- Scores: completeness=89.2, diversity=93.2, source=65.9, summary=96.5, freshness=100.0, retrieval=90.0, section_fit=100.0, core=93.5, commodity=93.8
- Briefing cards: 17 / Commodity cards: 15
- Sections: supply:4/5 raw=222, policy:5/5 raw=190, dist:5/5 raw=68, pest:3/5 raw=39
- Metrics: title_unique=1.00, domain_diversity=0.76, low_tier=0.24, summary_presence=1.00, summary_numeric=0.82, fresh_72h=1.00, fit_avg=4.30, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=8, commodity_active_today=12, commodity_active_today_unlinked=4, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.12, commodity_pool_false_link=0.00, commodity_dominant_section=0.62, semantic_penalty=0.0


### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1), pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
