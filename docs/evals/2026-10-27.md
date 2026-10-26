## Daily Eval (2026-10-27)
- Overall: **73.15** (warn)
- Operational: **87.10**
- Reader quality: **73.15** (capped; penalty=13.9, cap=90.0, reasons=pest_theme_duplicate)
- Scores: completeness=100.0, diversity=95.7, source=80.0, summary=97.0, freshness=100.0, retrieval=83.4, section_fit=87.5, core=99.1, commodity=100.0
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=312, policy:5/5 raw=105, dist:5/5 raw=85, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=1.00, low_tier=0.20, summary_presence=1.00, summary_numeric=0.60, fresh_72h=1.00, fit_avg=3.59, false_positive=0.05, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.8, commodity_weak=0.00, commodity_items=9, commodity_active_today=12, commodity_active_today_unlinked=3, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.44, semantic_penalty=6.0


### Editorial Shadow Eval
- Editorial: skipped (guaranteed_delivery_final)
- Model: gpt-5.6-sol

### Improvement Hints
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 5%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
