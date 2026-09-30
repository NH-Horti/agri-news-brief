## Daily Eval (2026-10-01)
- Overall: **71.15** (warn)
- Operational: **96.12**
- Reader quality: **95.49** (clear; penalty=0.6, cap=100.0, reasons=clear)
- Quality gate: **71.15** (needs_major_iteration, editorial_blocking_issue; editorial=71.2, operational=96.1)
- Scores: completeness=100.0, diversity=97.9, source=89.4, summary=100.0, freshness=100.0, retrieval=78.1, section_fit=93.8, core=100.0, commodity=87.0
- Briefing cards: 17 / Commodity cards: 21
- Sections: supply:5/5 raw=199, policy:5/5 raw=67, dist:5/5 raw=48, pest:2/2 raw=7
- Metrics: title_unique=1.00, domain_diversity=0.71, low_tier=0.18, summary_presence=1.00, summary_numeric=0.82, fresh_72h=1.00, fit_avg=2.67, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=6, commodity_active_today=12, commodity_active_today_unlinked=6, commodity_coverage=0.18, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=1.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **71.15** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 72.30; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=0, reasons=editorial_score_min, no_blocking_issues, critical_components_min, all_components_min, section_count_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 87.5 (underfilled)
- Components: article_selection=68.0, section_fit=72.0, core=70.0, summary=89.0, missed=66.0, noise=61.0
- Summary: 요약은 명료하지만 공급·유통에서 홍보성·비관련 꼬리기사가 강한 후보를 밀어냈다. 특히 유통의 장학금 기사는 농산물 유통과 무관하며, 수급조절위원회는 정책 섹션이 적합하다.
- [blocking] off_topic: 성주농협, 조합원 대학생 자녀 장학금 전달 - 장학금 전달식은 농산물 유통·물류·판로와 직접 관련이 없다.
- [moderate] wrong_section: 위상 높인 농산물 수급조절위 8기 닻 올려… "과수까지 품고 수급관리 ... - 법정위원회 격상과 농안법 시행이 중심인 정책 기사다.
- [moderate] promotional_filler: 수확 뒤 과수 수세 회복···조비, 감사비료 2종 제안 - 특정 업체 제품 제안 중심의 상업성 기사다.
- [moderate] weak_core: 롯데마트·슈퍼, 김장철 앞두고 절임 배추 물량 20% 늘린다 - 단일 유통업체 예약판매 기사여서 공급 핵심기사로는 범위가 좁다. 코어에서 내려야 한다.
- [moderate] weak_core: 2025년도 면적당 농산물 소득 7.7% 줄었다 - 전국 5300농가 조사에 기반한 핵심 경영지표로 현재 비코어 배치가 약하다. 코어로 올려야 한다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=18%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
