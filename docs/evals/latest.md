## Daily Eval (2026-10-21)
- Overall: **88.00** (pass)
- Operational: **94.13**
- Reader quality: **88.00** (capped; penalty=1.5, cap=88.0, reasons=commodity_false_link)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=70.5, section_fit=90.2, core=82.4, commodity=78.0
- Briefing cards: 17 / Commodity cards: 41
- Sections: supply:5/5 raw=254, policy:5/5 raw=72, dist:5/5 raw=82, pest:2/2 raw=3
- Metrics: title_unique=1.00, domain_diversity=0.88, low_tier=0.06, summary_presence=1.00, summary_numeric=0.82, fresh_72h=1.00, fit_avg=4.04, false_positive=0.00, hard_reader_issues=0, weak_core=0.09, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=12, commodity_active_today=18, commodity_active_today_unlinked=6, commodity_coverage=0.36, commodity_strict_link=0.75, commodity_false_link=0.08, commodity_pool_false_link=0.00, commodity_dominant_section=0.83, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: error (429 Client Error: Too Many Requests for url: https://api.openai.com/v1/responses)
- Model: gpt-5.6-sol

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 6%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
