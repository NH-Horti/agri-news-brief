## Daily Eval (2026-09-14)
- Overall: **83.76** (warn)
- Operational: **93.87**
- Reader quality: **83.76** (capped; penalty=10.1, cap=90.0, reasons=pest_theme_duplicate, commodity_pool_false_link)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=91.4, retrieval=89.8, section_fit=100.0, core=90.0, commodity=90.6
- Briefing cards: 20 / Commodity cards: 39
- Sections: supply:5/5 raw=329, policy:5/5 raw=141, dist:5/5 raw=73, pest:5/5 raw=28
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.15, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=4.79, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=3.0, commodity_weak=0.00, commodity_items=10, commodity_active_today=22, commodity_active_today_unlinked=12, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.07, commodity_dominant_section=0.70, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (editorial_budget_exhausted_after_repair)
- Model: gpt-5.6-sol

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=15%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
