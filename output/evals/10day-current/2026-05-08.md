## Daily Eval (2026-05-08)
- Overall: **81.24** (warn)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.0, section_fit=77.8, core=95.1, commodity=91.3
- Briefing cards: 17 / Commodity cards: 71
- Sections: supply:5/3 raw=168, policy:4/3 raw=162, dist:3/3 raw=43, pest:5/3 raw=30
- Metrics: title_unique=1.00, domain_diversity=0.94, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=3.47, false_positive=0.12, weak_core=0.14, commodity_weak=0.00, semantic_penalty=14.1

### Improvement Hints
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 리콜 시드 결손이 보입니다: dist, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 12%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 12%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
