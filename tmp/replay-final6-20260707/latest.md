## Daily Eval (2026-07-07)
- Overall: **89.01** (pass)
- Operational: **92.81**
- Reader quality: **89.01** (capped; penalty=3.8, cap=95.0, reasons=preferred_slot_underfill)
- Scores: completeness=92.8, diversity=94.2, source=71.1, summary=96.7, freshness=100.0, retrieval=87.5, section_fit=100.0, core=100.0, commodity=89.4
- Briefing cards: 18 / Commodity cards: 41
- Sections: supply:4/5 raw=250, policy:5/5 raw=109, dist:5/5 raw=84, pest:4/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.83, low_tier=0.22, summary_presence=1.00, summary_numeric=0.83, fresh_72h=1.00, fit_avg=4.43, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=11, commodity_active_today=14, commodity_active_today_unlinked=3, commodity_coverage=0.33, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.73, semantic_penalty=0.0


### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1), pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (dist_weak_ops=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
