## Daily Eval (2026-07-09)
- Overall: **93.12** (pass)
- Operational: **94.81**
- Reader quality: **93.12** (capped; penalty=1.7, cap=95.0, reasons=preferred_slot_underfill)
- Scores: completeness=96.4, diversity=90.3, source=75.8, summary=100.0, freshness=100.0, retrieval=90.0, section_fit=100.0, core=92.6, commodity=96.1
- Briefing cards: 19 / Commodity cards: 12
- Sections: supply:5/5 raw=180, policy:5/5 raw=138, dist:5/5 raw=59, pest:4/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.63, low_tier=0.21, summary_presence=1.00, summary_numeric=0.84, fresh_72h=1.00, fit_avg=4.66, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=7, commodity_active_today=11, commodity_active_today_unlinked=4, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Improvement Hints
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
