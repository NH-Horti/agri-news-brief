## Daily Eval (2026-11-19)
- Overall: **96.35** (pass)
- Operational: **96.53**
- Reader quality: **96.35** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=91.0, freshness=100.0, retrieval=87.5, section_fit=100.0, core=92.6, commodity=91.9
- Briefing cards: 20 / Commodity cards: 59
- Sections: supply:5/5 raw=319, policy:5/5 raw=105, dist:5/5 raw=78, pest:5/5 raw=54
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.32, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=10, commodity_active_today=18, commodity_active_today_unlinked=8, commodity_coverage=0.30, commodity_strict_link=0.80, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.60, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
