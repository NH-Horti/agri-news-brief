## Daily Eval (2026-11-05)
- Overall: **93.31** (pass)
- Operational: **93.31**
- Reader quality: **93.31** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=88.9, source=80.0, summary=89.5, freshness=100.0, retrieval=78.9, section_fit=100.0, core=89.5, commodity=88.4
- Briefing cards: 20 / Commodity cards: 57
- Sections: supply:5/5 raw=380, policy:5/5 raw=128, dist:5/5 raw=84, pest:5/5 raw=15
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.20, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.92, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=12, commodity_active_today=20, commodity_active_today_unlinked=8, commodity_coverage=0.36, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.75, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
