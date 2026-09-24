## Daily Eval (2026-08-25)
- Overall: **89.58** (pass)
- Operational: **92.52**
- Reader quality: **89.58** (clear; penalty=2.9, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=92.0, source=60.0, summary=92.5, freshness=100.0, retrieval=90.0, section_fit=88.8, core=100.0, commodity=92.0
- Briefing cards: 20 / Commodity cards: 47
- Sections: supply:5/5 raw=268, policy:5/5 raw=72, dist:5/5 raw=65, pest:5/5 raw=51
- Metrics: title_unique=1.00, domain_diversity=0.90, low_tier=0.25, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=4.38, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.8, commodity_weak=0.00, commodity_items=9, commodity_active_today=19, commodity_active_today_unlinked=10, commodity_coverage=0.27, commodity_strict_link=0.89, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (forced_sla_recovery)
- Model: gpt-5.6-sol

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
