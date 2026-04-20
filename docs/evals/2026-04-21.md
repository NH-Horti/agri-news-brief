## Daily Eval (2026-04-21)
- Overall: **93.82** (pass)
- Scores: completeness=100.0, diversity=98.8, summary=81.2, freshness=100.0, retrieval=86.2, section_fit=90.2, core=100.0, commodity=86.5
- Briefing cards: 16 / Commodity cards: 32
- Sections: supply:5/3 raw=146, policy:3/3 raw=172, dist:3/3 raw=41, pest:5/3 raw=31
- Metrics: title_unique=0.94, domain_diversity=0.69, summary_presence=1.00, summary_numeric=0.81, fresh_72h=1.00, fit_avg=3.49, weak_core=0.00, commodity_weak=0.00

### Improvement Hints
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 품목명 직접 언급, 수급/가격 신호, representative rank 상위 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: dist, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
