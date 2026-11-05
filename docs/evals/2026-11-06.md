## Daily Eval (2026-11-06)
- Overall: **83.32** (warn)
- Operational: **89.64**
- Reader quality: **83.32** (capped; penalty=6.3, cap=95.0, reasons=preferred_slot_underfill)
- Scores: completeness=96.4, diversity=95.2, source=75.8, summary=89.0, freshness=100.0, retrieval=75.6, section_fit=100.0, core=95.4, commodity=81.1
- Briefing cards: 19 / Commodity cards: 64
- Sections: supply:5/5 raw=407, policy:5/5 raw=100, dist:5/5 raw=75, pest:4/5 raw=13
- Metrics: title_unique=1.00, domain_diversity=0.74, low_tier=0.21, summary_presence=1.00, summary_numeric=0.53, fresh_72h=1.00, fit_avg=3.61, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=2.7, commodity_weak=0.00, commodity_items=14, commodity_active_today=20, commodity_active_today_unlinked=6, commodity_coverage=0.42, commodity_strict_link=0.71, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
