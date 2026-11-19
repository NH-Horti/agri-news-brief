## Daily Eval (2026-11-20)
- Overall: **86.41** (pass)
- Operational: **91.01**
- Reader quality: **86.41** (capped; penalty=4.6, cap=95.0, reasons=preferred_slot_underfill)
- Scores: completeness=92.8, diversity=98.7, source=93.3, summary=90.0, freshness=100.0, retrieval=75.7, section_fit=96.7, core=99.0, commodity=81.9
- Briefing cards: 18 / Commodity cards: 30
- Sections: supply:5/5 raw=298, policy:5/5 raw=93, dist:5/5 raw=96, pest:3/5 raw=14
- Metrics: title_unique=1.00, domain_diversity=0.83, low_tier=0.17, summary_presence=1.00, summary_numeric=0.67, fresh_72h=1.00, fit_avg=3.54, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.9, commodity_weak=0.00, commodity_items=9, commodity_active_today=16, commodity_active_today_unlinked=7, commodity_coverage=0.27, commodity_strict_link=0.78, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.78, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (guaranteed_delivery_final)
- Model: gpt-5.6-sol

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
