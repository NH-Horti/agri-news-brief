## Daily Eval (2026-11-17)
- Overall: **93.07** (pass)
- Operational: **94.57**
- Reader quality: **93.07** (clear; penalty=1.5, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=92.0, source=60.0, summary=94.0, freshness=100.0, retrieval=87.5, section_fit=100.0, core=100.0, commodity=89.4
- Briefing cards: 20 / Commodity cards: 99
- Sections: supply:5/5 raw=403, policy:5/5 raw=103, dist:5/5 raw=118, pest:5/5 raw=54
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.25, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=3.68, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=11, commodity_active_today=14, commodity_active_today_unlinked=3, commodity_coverage=0.33, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.73, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
