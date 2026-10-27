## Daily Eval (2026-10-28)
- Overall: **92.89** (pass)
- Operational: **93.64**
- Reader quality: **92.89** (capped; penalty=0.8, cap=95.0, reasons=preferred_slot_underfill)
- Scores: completeness=96.4, diversity=95.2, source=75.8, summary=96.8, freshness=100.0, retrieval=78.3, section_fit=96.9, core=87.7, commodity=96.1
- Briefing cards: 19 / Commodity cards: 31
- Sections: supply:5/5 raw=282, policy:5/5 raw=75, dist:5/5 raw=83, pest:4/5 raw=16
- Metrics: title_unique=1.00, domain_diversity=0.79, low_tier=0.21, summary_presence=1.00, summary_numeric=0.79, fresh_72h=1.00, fit_avg=3.65, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=7, commodity_active_today=15, commodity_active_today_unlinked=8, commodity_coverage=0.21, commodity_strict_link=0.86, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
