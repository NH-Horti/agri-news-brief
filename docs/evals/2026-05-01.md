## Daily Eval (2026-05-01)
- Overall: **93.66** (pass)
- Scores: completeness=100.0, diversity=96.7, summary=100.0, freshness=100.0, retrieval=86.2, section_fit=84.6, core=68.7, commodity=88.0
- Briefing cards: 15 / Commodity cards: 46
- Sections: supply:4/3 raw=169, policy:3/3 raw=83, dist:4/3 raw=34, pest:4/2 raw=14
- Metrics: title_unique=1.00, domain_diversity=0.67, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=1.90, weak_core=0.50, commodity_weak=0.07

### Improvement Hints
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
