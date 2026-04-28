## Daily Eval (2026-04-29)
- Overall: **94.31** (pass)
- Scores: completeness=94.0, diversity=99.2, summary=100.0, freshness=100.0, retrieval=87.5, section_fit=89.7, core=75.3, commodity=92.3
- Briefing cards: 13 / Commodity cards: 42
- Sections: supply:4/3 raw=134, policy:2/3 raw=104, dist:4/3 raw=63, pest:3/3 raw=37
- Metrics: title_unique=1.00, domain_diversity=0.69, summary_presence=1.00, summary_numeric=0.92, fresh_72h=1.00, fit_avg=2.56, weak_core=0.43, commodity_weak=0.00

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: policy. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
