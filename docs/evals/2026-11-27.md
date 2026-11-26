## Daily Eval (2026-11-27)
- Overall: **94.62** (pass)
- Operational: **95.70**
- Reader quality: **94.62** (clear; penalty=1.1, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=91.0, freshness=100.0, retrieval=91.9, section_fit=97.2, core=81.8, commodity=100.0
- Briefing cards: 20 / Commodity cards: 57
- Sections: supply:5/5 raw=375, policy:5/5 raw=131, dist:5/5 raw=101, pest:5/5 raw=61
- Metrics: title_unique=1.00, domain_diversity=0.80, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.65, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.6, commodity_weak=0.00, commodity_items=15, commodity_active_today=19, commodity_active_today_unlinked=4, commodity_coverage=0.45, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.47, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
