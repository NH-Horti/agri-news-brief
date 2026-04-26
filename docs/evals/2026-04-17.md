## Daily Eval (2026-04-17)
- Overall: **91.73** (pass)
- Scores: completeness=87.0, diversity=83.8, summary=100.0, freshness=100.0, retrieval=85.0, section_fit=95.0, core=100.0, commodity=80.8
- Briefing cards: 13 / Commodity cards: 30
- Sections: supply:2/3 raw=150, policy:3/3 raw=110, dist:3/3 raw=36, pest:5/3 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.54, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=3.28, weak_core=0.00, commodity_weak=0.00

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: supply. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 품목명 직접 언급, 수급/가격 신호, representative rank 상위 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: dist, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
