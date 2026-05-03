## Daily Eval (2026-05-04)
- Overall: **95.13** (pass)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=96.1, retrieval=84.4, section_fit=87.1, core=88.0, commodity=86.1
- Briefing cards: 14 / Commodity cards: 32
- Sections: supply:3/3 raw=109, policy:4/3 raw=61, dist:3/3 raw=26, pest:4/2 raw=21
- Metrics: title_unique=1.00, domain_diversity=0.79, summary_presence=1.00, summary_numeric=0.93, fresh_72h=1.00, fit_avg=3.10, weak_core=0.25, commodity_weak=0.00

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: supply, dist, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
