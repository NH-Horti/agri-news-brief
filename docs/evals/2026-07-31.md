## Daily Eval (2026-07-31)
- Overall: **77.47** (warn)
- Operational: **85.47**
- Reader quality: **77.47** (capped; penalty=8.0, cap=95.0, reasons=preferred_slot_underfill)
- Scores: completeness=92.8, diversity=91.8, source=71.1, summary=98.3, freshness=100.0, retrieval=84.7, section_fit=87.4, core=100.0, commodity=90.9
- Briefing cards: 18 / Commodity cards: 48
- Sections: supply:5/5 raw=319, policy:5/5 raw=111, dist:5/5 raw=67, pest:3/5 raw=26
- Metrics: title_unique=1.00, domain_diversity=0.67, low_tier=0.22, summary_presence=1.00, summary_numeric=0.61, fresh_72h=1.00, fit_avg=3.13, false_positive=0.06, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=13, commodity_active_today=19, commodity_active_today_unlinked=6, commodity_coverage=0.39, commodity_strict_link=0.92, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.69, semantic_penalty=6.7


### Editorial Shadow Eval
- Editorial: skipped (forced_sla_recovery)
- Model: gpt-5.6-sol

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 6%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 6%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
