## Daily Eval (2026-05-06)
- Overall: **97.78** (pass)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=83.8, section_fit=99.9, core=93.3, commodity=91.3
- Briefing cards: 16 / Commodity cards: 43
- Sections: supply:3/3 raw=141, policy:4/3 raw=121, dist:4/3 raw=38, pest:5/2 raw=13
- Metrics: title_unique=1.00, domain_diversity=0.81, summary_presence=1.00, summary_numeric=0.69, fresh_72h=1.00, fit_avg=3.73, false_positive=0.00, weak_core=0.14, commodity_weak=0.06, semantic_penalty=0.0

### Improvement Hints
- 리콜 시드 결손이 보입니다: supply, dist, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
