## Daily Eval (2026-04-15)
- Overall: **94.77** (pass)
- Scores: completeness=93.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.0, section_fit=95.2, core=92.5, commodity=69.6
- Briefing cards: 15 / Commodity cards: 26
- Sections: supply:3/3 raw=206, policy:4/3 raw=143, dist:3/3 raw=30, pest:5/3 raw=31
- Metrics: title_unique=1.00, domain_diversity=0.93, summary_presence=1.00, summary_numeric=0.87, fresh_72h=1.00, fit_avg=3.46, weak_core=0.20, commodity_weak=0.00

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 품목명 직접 언급, 수급/가격 신호, representative rank 상위 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: dist, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
