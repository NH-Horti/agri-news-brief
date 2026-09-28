## Daily Eval (2026-09-29)
- Overall: **62.59** (fail)
- Operational: **83.90**
- Reader quality: **70.41** (capped; penalty=13.5, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **62.59** (needs_major_iteration, editorial_major_issue; editorial=70.7, operational=83.9)
- Scores: completeness=82.0, diversity=90.7, source=53.3, summary=100.0, freshness=100.0, retrieval=84.8, section_fit=100.0, core=88.3, commodity=88.0
- Briefing cards: 15 / Commodity cards: 23
- Sections: supply:3/5 raw=162, policy:3/5 raw=63, dist:5/5 raw=66, pest:4/5 raw=27
- Metrics: title_unique=1.00, domain_diversity=1.00, low_tier=0.27, summary_presence=1.00, summary_numeric=0.87, fresh_72h=1.00, fit_avg=2.96, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=2.4, commodity_weak=0.00, commodity_items=8, commodity_active_today=12, commodity_active_today_unlinked=4, commodity_coverage=0.24, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.88, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **70.70** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 72.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=4, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, section_count_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 93.0 (soft_fallback)
- Components: article_selection=68.0, section_fit=84.0, core=61.0, summary=91.0, missed=55.0, noise=70.0
- Summary: 요약과 섹션 정합성은 대체로 좋지만, 수급·정책의 강한 전국·시장 후보를 놓치고 지역성 기사로 최소 편수만 채웠다. 병해충 핵심 선정도 위험 규모와 맞지 않는다.
- [major] underfill: 수급·정책·병해충 섹션 편수 부족 - 충분한 원시 후보가 있는데 각각 3·3·4건에 그쳐 목표 5건을 충족하지 못했다.
- [major] missed_candidate: [2026년 9월 5주] 주요 농산물 경락가 상승·하락 품목 - 쌈배추 145.8% 상승 등 실제 가격·출하 신호를 담은 최상위 수급 후보가 빠졌다.
- [moderate] weak_core: 제주, 드론 활용 극조생 감귤 수확 현장 단속 강화 - 지역 비상품 단속 기사로 전국 가격 동향 후보보다 핵심성이 낮다.
- [major] missed_candidate: '3중고' K-농업…소득·기술·CPTPP 모두 '위기' - 농업소득·경영비·통상 위험을 함께 다룬 전국 정책 의제가 지역 시스템 개발·지원 건의보다 중요하다.
- [moderate] weak_core: 충남도 농축산국, 생성형 AI로 농업업무 시스템 직접 개발 - 유용한 행정 혁신 사례지만 당일 전국 정책 의제를 대표하기에는 약하다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: supply, policy. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-2), policy(-2), pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=7%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
