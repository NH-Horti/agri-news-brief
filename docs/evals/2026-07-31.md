## Daily Eval (2026-07-31)
- Overall: **91.11** (pass)
- Operational: **92.61**
- Reader quality: **91.11** (capped; penalty=1.5, cap=95.0, reasons=preferred_slot_underfill)
- Scores: completeness=92.8, diversity=91.8, source=71.1, summary=96.7, freshness=100.0, retrieval=84.7, section_fit=96.7, core=94.7, commodity=90.9
- Briefing cards: 18 / Commodity cards: 49
- Sections: supply:5/5 raw=318, policy:5/5 raw=110, dist:5/5 raw=67, pest:3/5 raw=26
- Metrics: title_unique=1.00, domain_diversity=0.67, low_tier=0.22, summary_presence=1.00, summary_numeric=0.61, fresh_72h=1.00, fit_avg=3.06, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=13, commodity_active_today=19, commodity_active_today_unlinked=6, commodity_coverage=0.39, commodity_strict_link=0.92, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.69, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
