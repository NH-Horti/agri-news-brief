## Daily Eval (2026-09-18)
- Overall: **83.04** (warn)
- Operational: **88.22**
- Reader quality: **83.04** (clear; penalty=5.2, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=92.9, source=100.0, summary=100.0, freshness=100.0, retrieval=85.1, section_fit=88.8, core=82.0, commodity=88.0
- Briefing cards: 20 / Commodity cards: 25
- Sections: supply:5/5 raw=265, policy:5/5 raw=102, dist:5/5 raw=80, pest:5/5 raw=23
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.00, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.33, false_positive=0.05, hard_reader_issues=0, weak_core=0.09, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=6, commodity_active_today=14, commodity_active_today_unlinked=8, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.83, semantic_penalty=6.0


### Editorial Shadow Eval
- Editorial: skipped (editorial_budget_exhausted_after_repair)
- Model: gpt-5.6-sol

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 5%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
