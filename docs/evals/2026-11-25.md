## Daily Eval (2026-11-25)
- Overall: **88.65** (pass)
- Operational: **94.41**
- Reader quality: **88.65** (clear; penalty=5.8, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=97.0, freshness=100.0, retrieval=89.4, section_fit=100.0, core=100.0, commodity=93.3
- Briefing cards: 20 / Commodity cards: 44
- Sections: supply:5/5 raw=430, policy:5/5 raw=123, dist:5/5 raw=100, pest:5/5 raw=30
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.20, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.75, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=3.2, commodity_weak=0.00, commodity_items=11, commodity_active_today=14, commodity_active_today_unlinked=3, commodity_coverage=0.33, commodity_strict_link=0.91, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.64, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
