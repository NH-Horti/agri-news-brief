## Daily Eval (2026-10-14)
- Overall: **80.42** (warn)
- Operational: **89.58**
- Reader quality: **84.02** (capped; penalty=5.6, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **80.42** (needs_major_iteration, editorial_major_issue; editorial=77.6, operational=89.6)
- Scores: completeness=89.2, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=77.0, section_fit=90.2, core=89.2, commodity=88.0
- Briefing cards: 17 / Commodity cards: 29
- Sections: supply:4/5 raw=156, policy:5/5 raw=78, dist:4/5 raw=32, pest:4/5 raw=15
- Metrics: title_unique=1.00, domain_diversity=0.88, low_tier=0.12, summary_presence=1.00, summary_numeric=0.76, fresh_72h=1.00, fit_avg=3.64, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.6, commodity_weak=0.00, commodity_items=3, commodity_active_today=14, commodity_active_today_unlinked=11, commodity_coverage=0.09, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=1.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **77.60** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 78.60; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, section_count_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 94.0 (soft_fallback)
- Components: article_selection=76.0, section_fit=84.0, core=75.0, summary=90.0, missed=68.0, noise=73.0
- Summary: 핵심 수급·정책·유통 기사는 대체로 유용하지만, 3개 섹션이 4건에 그쳤고 행사·교육·제품 홍보성 꼬리가 품질을 낮췄다. 일부 지역 지원 기사의 코어 지정도 재조정이 필요하다.
- [moderate] underfill: 공급·유통·병해충 섹션 각 4건 편성 - 원시 후보가 충분한데 세 섹션 모두 목표 5건을 채우지 못했다.
- [major] promotional_filler: 송이 경매 의 짜릿함부터 내성천 송이라면의 별미까지 - 유통 현안보다 지역 축제와 먹거리 체험 홍보가 중심이다.
- [moderate] missed_candidate: 인천 계양농협, 산지 농협에 출하선급금 15억원 지원 - 구체적인 유통자금 지원으로 식품안전 교육·지역 행사보다 운영 가치가 높다.
- [major] promotional_filler: 한국삼공, 10월 추천 작물보호제 ‘제라진·플로빈’ - 특정 기업의 추천 제품 소개로 독립적인 병해충 위험 정보가 부족하다.
- [moderate] promotional_filler: 농식품부 청년자문단, 영농형 태양광 현장 방문… 정책 아이디어 발굴 - 정책 결정이나 사업 변화 없이 현장 방문 활동에 머문다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1), dist(-1), pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=6%, dist_weak_ops=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 6%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
