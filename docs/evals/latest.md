## Daily Eval (2026-08-07)
- Overall: **88.00** (pass)
- Operational: **95.24**
- Reader quality: **88.00** (capped; penalty=5.4, cap=88.0, reasons=commodity_false_link)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=97.2, core=85.0, commodity=97.5
- Briefing cards: 20 / Commodity cards: 42
- Sections: supply:5/5 raw=311, policy:5/5 raw=109, dist:5/5 raw=56, pest:5/5 raw=41
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.10, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=3.99, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.1, commodity_weak=0.00, commodity_items=11, commodity_active_today=18, commodity_active_today_unlinked=7, commodity_coverage=0.33, commodity_strict_link=0.82, commodity_false_link=0.09, commodity_pool_false_link=0.00, commodity_dominant_section=0.45, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (editorial_budget_exhausted_after_repair)
- Model: gpt-5.6-sol

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
