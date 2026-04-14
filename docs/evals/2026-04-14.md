## Daily Eval (2026-04-14)
- Overall: **93.42** (pass)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=68.3, core=94.3, commodity=73.3
- Briefing cards: 19 / Commodity cards: 48
- Sections: supply:5/3 raw=234, policy:4/3 raw=200, dist:5/2 raw=23, pest:5/3 raw=41
- Metrics: title_unique=1.00, domain_diversity=0.89, summary_presence=1.00, summary_numeric=0.84, fresh_72h=1.00, fit_avg=3.06, weak_core=0.14, commodity_weak=0.00

### Improvement Hints
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 품목명 직접 언급, 수급/가격 신호, representative rank 상위 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: dist, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
