## Daily Eval (2026-09-16)
- Overall: **84.23** (warn)
- Operational: **93.18**
- Reader quality: **84.23** (capped; penalty=8.9, cap=90.0, reasons=pest_theme_duplicate)
- Scores: completeness=100.0, diversity=92.2, source=100.0, summary=100.0, freshness=100.0, retrieval=87.9, section_fit=90.3, core=92.4, commodity=100.0
- Briefing cards: 20 / Commodity cards: 34
- Sections: supply:5/5 raw=267, policy:5/5 raw=130, dist:5/5 raw=91, pest:5/5 raw=27
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.19, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=2.8, commodity_weak=0.00, commodity_items=7, commodity_active_today=17, commodity_active_today_unlinked=10, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (forced_sla_recovery)
- Model: gpt-5.6-sol

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
