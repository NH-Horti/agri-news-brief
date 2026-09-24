## Daily Eval (2026-08-19)
- Overall: **82.55** (warn)
- Operational: **93.79**
- Reader quality: **82.55** (capped; penalty=11.2, cap=90.0, reasons=pest_theme_duplicate)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=88.1, section_fit=91.1, core=81.8, commodity=92.0
- Briefing cards: 20 / Commodity cards: 35
- Sections: supply:5/5 raw=249, policy:5/5 raw=55, dist:5/5 raw=120, pest:5/5 raw=63
- Metrics: title_unique=1.00, domain_diversity=0.80, low_tier=0.20, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=3.90, false_positive=0.00, hard_reader_issues=0, weak_core=0.11, editorial_penalty=1.8, commodity_weak=0.00, commodity_items=9, commodity_active_today=16, commodity_active_today_unlinked=7, commodity_coverage=0.27, commodity_strict_link=0.89, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (editorial_budget_exhausted_after_repair)
- Model: gpt-5.6-sol

### Improvement Hints
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=5%, promotional_filler=10%, pest_theme_duplicate=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
