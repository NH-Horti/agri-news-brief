## Daily Eval (2026-06-08)
- Overall: **94.40** (pass)
- Operational: **94.40**
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=93.8, retrieval=85.0, section_fit=96.9, core=92.8, commodity=93.8
- Briefing cards: 19 / Commodity cards: 27
- Sections: supply:5/5 raw=230, policy:5/5 raw=155, dist:4/5 raw=92, pest:5/5 raw=75
- Metrics: title_unique=1.00, domain_diversity=0.84, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=4.34, false_positive=0.00, weak_core=0.14, editorial_penalty=0.5, commodity_weak=0.00, commodity_coverage=0.24, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.62, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (missing_openai_api_key)

### Improvement Hints
- 품목 보드 coverage가 낮습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
