## Daily Eval (2026-11-02)
- Overall: **83.50** (warn)
- Operational: **87.10**
- Reader quality: **83.50** (clear; penalty=3.6, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=88.0, source=40.0, summary=83.5, freshness=90.0, retrieval=76.5, section_fit=100.0, core=96.3, commodity=80.7
- Briefing cards: 20 / Commodity cards: 51
- Sections: supply:5/5 raw=347, policy:5/5 raw=72, dist:5/5 raw=100, pest:5/5 raw=17
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.30, summary_presence=1.00, summary_numeric=0.50, fresh_72h=1.00, fit_avg=3.22, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=13, commodity_active_today=18, commodity_active_today_unlinked=5, commodity_coverage=0.39, commodity_strict_link=0.77, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.85, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
