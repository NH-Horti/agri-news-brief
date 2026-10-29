## Daily Eval (2026-10-30)
- Overall: **92.70** (pass)
- Operational: **94.14**
- Reader quality: **92.70** (clear; penalty=1.4, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=89.5, freshness=100.0, retrieval=76.6, section_fit=97.2, core=97.2, commodity=94.9
- Briefing cards: 20 / Commodity cards: 25
- Sections: supply:5/5 raw=251, policy:5/5 raw=71, dist:5/5 raw=59, pest:5/5 raw=18
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.20, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=3.56, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.8, commodity_weak=0.00, commodity_items=10, commodity_active_today=17, commodity_active_today_unlinked=7, commodity_coverage=0.30, commodity_strict_link=0.90, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.60, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: supply, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
