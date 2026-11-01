## Daily Eval (2026-10-26)
- Overall: **90.94** (pass)
- Operational: **91.30**
- Reader quality: **90.94** (clear; penalty=0.4, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=91.0, freshness=90.0, retrieval=79.7, section_fit=67.4, core=100.0, commodity=97.5
- Briefing cards: 20 / Commodity cards: 27
- Sections: supply:5/5 raw=341, policy:5/5 raw=100, dist:5/5 raw=83, pest:5/5 raw=17
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.15, summary_presence=1.00, summary_numeric=0.60, fresh_72h=1.00, fit_avg=2.83, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.2, commodity_weak=0.00, commodity_items=13, commodity_active_today=16, commodity_active_today_unlinked=3, commodity_coverage=0.39, commodity_strict_link=0.92, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.54, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 15%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
