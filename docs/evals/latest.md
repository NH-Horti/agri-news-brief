## Daily Eval (2026-09-15)
- Overall: **82.11** (warn)
- Operational: **93.38**
- Reader quality: **82.11** (capped; penalty=11.3, cap=90.0, reasons=pest_theme_duplicate, preferred_slot_underfill)
- Scores: completeness=96.4, diversity=99.4, source=96.8, summary=96.8, freshness=100.0, retrieval=87.8, section_fit=100.0, core=100.0, commodity=100.0
- Briefing cards: 19 / Commodity cards: 37
- Sections: supply:5/5 raw=215, policy:5/5 raw=115, dist:5/5 raw=69, pest:4/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.74, low_tier=0.16, summary_presence=1.00, summary_numeric=0.79, fresh_72h=1.00, fit_avg=4.85, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=3.2, commodity_weak=0.00, commodity_items=9, commodity_active_today=14, commodity_active_today_unlinked=5, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.44, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (forced_sla_recovery)
- Model: gpt-5.6-sol

### Improvement Hints
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=11%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
