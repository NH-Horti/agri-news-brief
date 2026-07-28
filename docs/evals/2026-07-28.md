## Daily Eval (2026-07-28)
- Overall: **79.53** (warn)
- Operational: **90.57**
- Reader quality: **79.53** (clear; penalty=11.0, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=92.0, source=60.0, summary=100.0, freshness=100.0, retrieval=88.8, section_fit=100.0, core=97.2, commodity=98.1
- Briefing cards: 20 / Commodity cards: 41
- Sections: supply:5/5 raw=176, policy:5/5 raw=113, dist:5/5 raw=64, pest:5/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.25, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.73, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=5.3, commodity_weak=0.00, commodity_items=12, commodity_active_today=16, commodity_active_today_unlinked=4, commodity_coverage=0.36, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: error (429 Client Error: Too Many Requests for url: https://api.openai.com/v1/responses)
- Model: gpt-5.6-sol

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=20%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
