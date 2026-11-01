## Daily Eval (2026-10-22)
- Overall: **94.80** (pass)
- Operational: **94.98**
- Reader quality: **94.80** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=95.1, source=80.0, summary=89.5, freshness=100.0, retrieval=77.3, section_fit=97.2, core=97.6, commodity=99.2
- Briefing cards: 20 / Commodity cards: 67
- Sections: supply:5/5 raw=274, policy:5/5 raw=88, dist:5/5 raw=118, pest:5/5 raw=19
- Metrics: title_unique=1.00, domain_diversity=0.80, low_tier=0.20, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=4.02, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=14, commodity_active_today=19, commodity_active_today_unlinked=5, commodity_coverage=0.42, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
