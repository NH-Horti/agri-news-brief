## Daily Eval (2026-04-13)
- Overall: **87.68** (pass)
- Scores: completeness=88.0, diversity=100.0, summary=100.0, freshness=77.8, retrieval=86.2, section_fit=71.2, core=81.4, commodity=81.2
- Briefing cards: 13 / Commodity cards: 47
- Sections: supply:5/3 raw=177, policy:3/3 raw=153, dist:1/3 raw=45, pest:4/3 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.85, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.12, weak_core=0.33, commodity_weak=0.00

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: dist. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 품목명 직접 언급, 수급/가격 신호, representative rank 상위 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
