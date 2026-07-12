## Daily Eval (2026-07-06)
- Overall: **94.47** (pass)
- Operational: **95.19**
- Reader quality: **94.47** (clear; penalty=0.7, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=96.4, source=100.0, summary=92.5, freshness=91.4, retrieval=89.4, section_fit=95.8, core=100.0, commodity=99.8
- Briefing cards: 20 / Commodity cards: 29
- Sections: supply:5/5 raw=255, policy:5/5 raw=138, dist:5/5 raw=100, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.65, low_tier=0.15, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=4.29, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=11, commodity_active_today=16, commodity_active_today_unlinked=5, commodity_coverage=0.33, commodity_strict_link=0.91, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.45, semantic_penalty=0.0


### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
