## Daily Eval (2026-09-28)
- Overall: **70.62** (warn)
- Operational: **83.48**
- Reader quality: **70.62** (capped; penalty=12.9, cap=90.0, reasons=pest_theme_duplicate)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=25.0, retrieval=90.0, section_fit=100.0, core=84.7, commodity=71.0
- Briefing cards: 20 / Commodity cards: 41
- Sections: supply:5/5 raw=347, policy:5/5 raw=204, dist:5/5 raw=65, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=0.25, fit_avg=3.53, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.7, commodity_weak=0.00, commodity_items=10, commodity_active_today=20, commodity_active_today_unlinked=10, commodity_coverage=0.30, commodity_strict_link=0.70, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.80, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (editorial_budget_exhausted_after_repair)
- Model: gpt-5.6-sol

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 최신성 점수가 내려갔습니다. 동일 이벤트 중 최신 기사 우선, 96시간 초과 기사 감점을 더 강하게 주는 편이 안정적입니다.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 오래된 기사일수록 배경 설명은 줄이고 이번 보고일 기준으로 새롭게 확인된 조치나 수급 신호를 먼저 적는다.
