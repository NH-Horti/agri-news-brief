## Daily Eval (2026-04-30)
- Overall: **96.50** (pass)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.2, section_fit=90.3, core=86.5, commodity=94.1
- Briefing cards: 18 / Commodity cards: 96
- Sections: supply:5/3 raw=197, policy:4/3 raw=131, dist:4/3 raw=45, pest:5/3 raw=64
- Metrics: title_unique=1.00, domain_diversity=0.83, summary_presence=1.00, summary_numeric=0.78, fresh_72h=1.00, fit_avg=2.53, weak_core=0.25, commodity_weak=0.00

### Improvement Hints
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
