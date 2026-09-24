## Daily Eval (2026-08-04)
- Overall: **81.67** (warn)
- Operational: **90.35**
- Reader quality: **81.67** (capped; penalty=8.7, cap=90.0, reasons=pest_theme_duplicate)
- Scores: completeness=100.0, diversity=88.0, source=40.0, summary=100.0, freshness=100.0, retrieval=82.5, section_fit=92.4, core=94.7, commodity=88.0
- Briefing cards: 20 / Commodity cards: 34
- Sections: supply:5/5 raw=306, policy:5/5 raw=60, dist:5/5 raw=70, pest:5/5 raw=21
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.30, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=2.45, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.6, commodity_weak=0.00, commodity_items=10, commodity_active_today=18, commodity_active_today_unlinked=8, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.80, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (forced_sla_recovery)
- Model: gpt-5.6-sol

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
