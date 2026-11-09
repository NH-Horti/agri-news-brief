## Daily Eval (2026-11-10)
- Overall: **86.07** (pass)
- Operational: **91.85**
- Reader quality: **86.07** (clear; penalty=5.8, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=98.2, source=96.8, summary=96.8, freshness=100.0, retrieval=73.1, section_fit=94.7, core=84.2, commodity=95.6
- Briefing cards: 19 / Commodity cards: 35
- Sections: supply:5/5 raw=246, policy:5/5 raw=101, dist:5/5 raw=56, pest:4/4 raw=9
- Metrics: title_unique=1.00, domain_diversity=0.68, low_tier=0.16, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=2.79, false_positive=0.00, hard_reader_issues=0, weak_core=0.17, editorial_penalty=3.2, commodity_weak=0.00, commodity_items=12, commodity_active_today=17, commodity_active_today_unlinked=5, commodity_coverage=0.36, commodity_strict_link=0.92, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.58, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=11%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
