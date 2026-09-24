## Daily Eval (2026-08-20)
- Overall: **75.77** (warn)
- Operational: **84.37**
- Reader quality: **75.77** (clear; penalty=8.6, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=88.0, source=40.0, summary=92.5, freshness=100.0, retrieval=82.4, section_fit=91.7, core=100.0, commodity=94.9
- Briefing cards: 20 / Commodity cards: 50
- Sections: supply:5/5 raw=232, policy:5/5 raw=76, dist:5/5 raw=117, pest:5/5 raw=20
- Metrics: title_unique=1.00, domain_diversity=0.90, low_tier=0.30, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=3.91, false_positive=0.05, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=10, commodity_active_today=17, commodity_active_today_unlinked=7, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.60, semantic_penalty=6.0


### Editorial Shadow Eval
- Editorial: skipped (forced_sla_recovery)
- Model: gpt-5.6-sol

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 5%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
