## Daily Eval (2026-09-23)
- Overall: **81.37** (warn)
- Operational: **93.65**
- Reader quality: **81.37** (capped; penalty=12.3, cap=90.0, reasons=pest_theme_duplicate)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=91.9, section_fit=100.0, core=85.0, commodity=99.0
- Briefing cards: 20 / Commodity cards: 23
- Sections: supply:5/5 raw=217, policy:5/5 raw=147, dist:5/5 raw=84, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.10, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.18, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=4.6, commodity_weak=0.00, commodity_items=6, commodity_active_today=16, commodity_active_today_unlinked=10, commodity_coverage=0.18, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.33, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (editorial_budget_exhausted_after_repair)
- Model: gpt-5.6-sol

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
