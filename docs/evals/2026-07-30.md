## Daily Eval (2026-07-30)
- Overall: **80.36** (warn)
- Operational: **90.48**
- Reader quality: **80.36** (capped; penalty=10.1, cap=90.0, reasons=pest_theme_duplicate)
- Scores: completeness=100.0, diversity=88.0, source=40.0, summary=92.5, freshness=100.0, retrieval=90.0, section_fit=98.6, core=100.0, commodity=96.1
- Briefing cards: 20 / Commodity cards: 29
- Sections: supply:5/5 raw=238, policy:5/5 raw=127, dist:5/5 raw=59, pest:5/5 raw=68
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.30, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=3.72, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=1.4, commodity_weak=0.00, commodity_items=7, commodity_active_today=14, commodity_active_today_unlinked=7, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, dist_weak_ops=10%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
