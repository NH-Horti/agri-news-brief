## Daily Eval (2026-07-29)
- Overall: **92.97** (pass)
- Operational: **94.66**
- Reader quality: **92.97** (capped; penalty=1.7, cap=95.0, reasons=preferred_slot_underfill)
- Scores: completeness=96.4, diversity=95.2, source=75.8, summary=93.7, freshness=100.0, retrieval=88.1, section_fit=100.0, core=100.0, commodity=88.4
- Briefing cards: 19 / Commodity cards: 35
- Sections: supply:5/5 raw=209, policy:4/5 raw=134, dist:5/5 raw=55, pest:5/5 raw=71
- Metrics: title_unique=1.00, domain_diversity=0.74, low_tier=0.21, summary_presence=1.00, summary_numeric=0.68, fresh_72h=1.00, fit_avg=3.75, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=4, commodity_active_today=18, commodity_active_today_unlinked=14, commodity_coverage=0.12, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.75, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (forced_sla_recovery)
- Model: gpt-5.6-sol

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
