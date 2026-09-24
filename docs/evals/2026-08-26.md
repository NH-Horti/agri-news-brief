## Daily Eval (2026-08-26)
- Overall: **85.33** (pass)
- Operational: **92.35**
- Reader quality: **85.33** (clear; penalty=7.0, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=89.5, freshness=100.0, retrieval=88.8, section_fit=100.0, core=100.0, commodity=91.0
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=348, policy:5/5 raw=82, dist:5/5 raw=65, pest:5/5 raw=39
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.20, summary_presence=1.00, summary_numeric=0.60, fresh_72h=1.00, fit_avg=3.34, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=3.9, commodity_weak=0.00, commodity_items=12, commodity_active_today=17, commodity_active_today_unlinked=5, commodity_coverage=0.36, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (forced_sla_recovery)
- Model: gpt-5.6-sol

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=5%, promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
