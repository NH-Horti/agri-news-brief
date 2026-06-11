## Daily Eval (2026-06-11)
- Overall: **96.57** (pass)
- Operational: **96.57**
- Scores: completeness=100.0, diversity=90.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=98.0, commodity=99.1
- Briefing cards: 20 / Commodity cards: 14
- Sections: supply:5/5 raw=141, policy:5/5 raw=105, dist:5/5 raw=40, pest:5/5 raw=41
- Metrics: title_unique=1.00, domain_diversity=0.60, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.13, false_positive=0.00, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_strict_link=1.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (missing_openai_api_key)

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
