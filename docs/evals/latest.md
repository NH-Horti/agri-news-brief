## Daily Eval (2026-04-22)
- Overall: **96.09** (pass)
- Scores: completeness=100.0, diversity=100.0, summary=94.7, freshness=100.0, retrieval=84.4, section_fit=89.8, core=100.0, commodity=88.2
- Briefing cards: 17 / Commodity cards: 22
- Sections: supply:5/3 raw=182, policy:4/3 raw=141, dist:3/3 raw=42, pest:5/3 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.71, summary_presence=1.00, summary_numeric=0.82, fresh_72h=1.00, fit_avg=2.56, weak_core=0.00, commodity_weak=0.00

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 품목명 직접 언급, 수급/가격 신호, representative rank 상위 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
