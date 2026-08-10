## Daily Eval (2026-08-11)
- Overall: **84.00** (warn)
- Operational: **92.62**
- Reader quality: **84.00** (capped; penalty=8.2, cap=84.0, reasons=pest_theme_duplicate, commodity_false_link, commodity_false_link_severe)
- Scores: completeness=100.0, diversity=92.0, source=60.0, summary=97.0, freshness=100.0, retrieval=82.8, section_fit=100.0, core=79.3, commodity=85.2
- Briefing cards: 20 / Commodity cards: 28
- Sections: supply:5/5 raw=256, policy:5/5 raw=84, dist:5/5 raw=39, pest:5/5 raw=26
- Metrics: title_unique=1.00, domain_diversity=0.90, low_tier=0.25, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=3.85, false_positive=0.00, hard_reader_issues=0, weak_core=0.29, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=9, commodity_active_today=14, commodity_active_today_unlinked=5, commodity_coverage=0.27, commodity_strict_link=0.89, commodity_false_link=0.11, commodity_pool_false_link=0.00, commodity_dominant_section=0.78, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (forced_sla_recovery)
- Model: gpt-5.6-sol

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
