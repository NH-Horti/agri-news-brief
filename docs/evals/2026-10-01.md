## Daily Eval (2026-10-01)
- Overall: **90.98** (warn)
- Operational: **94.52**
- Reader quality: **92.57** (capped; penalty=1.9, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **90.98** (needs_major_iteration, editorial_acceptance_gate_failed; editorial=75.7, operational=94.5)
- Scores: completeness=96.4, diversity=99.1, source=100.0, summary=100.0, freshness=100.0, retrieval=78.1, section_fit=93.0, core=100.0, commodity=87.0
- Briefing cards: 16 / Commodity cards: 21
- Sections: supply:5/5 raw=199, policy:5/5 raw=67, dist:4/5 raw=48, pest:2/2 raw=7
- Metrics: title_unique=1.00, domain_diversity=0.69, low_tier=0.12, summary_presence=1.00, summary_numeric=0.81, fresh_72h=1.00, fit_avg=2.74, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.2, commodity_weak=0.00, commodity_items=6, commodity_active_today=12, commodity_active_today_unlinked=6, commodity_coverage=0.18, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=1.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **75.65** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 77.10; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, section_count_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 85.5 (underfilled)
- Components: article_selection=74.0, section_fit=72.0, core=79.0, summary=88.0, missed=69.0, noise=70.0
- Summary: 핵심 정책·유통 이슈는 일부 잘 잡았지만, 정책 기사를 공급에 배치하고 홍보성·지역 지원 기사를 채워 넣은 탓에 편집 밀도가 낮다. 특히 dist를 4건으로 두면서도 김치교실을 유지한 선택이 아쉽다.
- [moderate] wrong_section: 위상 높인 농산물 수급조절위 8기 닻 올려 - 법정위원회 격상과 농안법 시행을 다룬 명백한 정책 기사다.
- [moderate] weak_core: 위상 높인 농산물 수급조절위 8기 닻 올려 - 농산물 수급관리 체계의 전국적 변화를 다뤄 지역 정치 간담회보다 핵심성이 높다.
- [moderate] promotional_filler: 수확 뒤 과수 수세 회복···조비, 감사비료 2종 제안 - 특정 업체 비료 제품 제안이 중심인 판촉성 콘텐츠다.
- [moderate] promotional_filler: 추석 농축산물 할인, 장바구니 너머 농가의 이야기도 들어보니 - 할인정책의 효과 분석보다 정책 홍보와 체험담 성격이 강하다.
- [moderate] wrong_section: 천안농협, 폭염·가뭄 피해 예방 영농자재 전달 - 지역 농협의 자재 지원 사례로 정책 제도나 결정과의 연관성이 약하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=12%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
