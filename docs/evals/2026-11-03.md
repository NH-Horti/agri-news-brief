## Daily Eval (2026-11-03)
- Overall: **93.00** (pass)
- Operational: **94.08**
- Reader quality: **93.00** (clear; penalty=1.1, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=86.5, freshness=100.0, retrieval=70.4, section_fit=100.0, core=99.6, commodity=99.1
- Briefing cards: 20 / Commodity cards: 50
- Sections: supply:5/5 raw=285, policy:5/5 raw=90, dist:5/5 raw=77, pest:5/5 raw=10
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.20, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=3.60, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.6, commodity_weak=0.00, commodity_items=8, commodity_active_today=14, commodity_active_today_unlinked=6, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
