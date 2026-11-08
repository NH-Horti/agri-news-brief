## Daily Eval (2026-11-09)
- Overall: **86.15** (pass)
- Operational: **89.93**
- Reader quality: **86.15** (clear; penalty=3.8, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=88.0, source=40.0, summary=91.0, freshness=90.0, retrieval=86.7, section_fit=100.0, core=96.2, commodity=99.1
- Briefing cards: 20 / Commodity cards: 61
- Sections: supply:5/5 raw=403, policy:5/5 raw=125, dist:5/5 raw=135, pest:5/5 raw=28
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.30, summary_presence=1.00, summary_numeric=0.55, fresh_72h=1.00, fit_avg=3.31, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=10, commodity_active_today=19, commodity_active_today_unlinked=9, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
