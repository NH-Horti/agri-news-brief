## Daily Eval (2026-09-29)
- Overall: **62.33** (fail)
- Operational: **82.27**
- Reader quality: **67.03** (capped; penalty=15.2, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **62.33** (needs_major_iteration, editorial_major_issue; editorial=73.2, operational=82.3)
- Scores: completeness=78.4, diversity=89.1, source=45.7, summary=100.0, freshness=100.0, retrieval=84.8, section_fit=100.0, core=88.3, commodity=88.0
- Briefing cards: 14 / Commodity cards: 23
- Sections: supply:3/5 raw=163, policy:3/5 raw=63, dist:5/5 raw=66, pest:3/5 raw=27
- Metrics: title_unique=1.00, domain_diversity=1.00, low_tier=0.29, summary_presence=1.00, summary_numeric=0.86, fresh_72h=1.00, fit_avg=3.08, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=2.4, commodity_weak=0.00, commodity_items=8, commodity_active_today=12, commodity_active_today_unlinked=4, commodity_coverage=0.24, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.88, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **73.20** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 72.80; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, section_count_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 92.5 (minimum_fallback)
- Components: article_selection=70.0, section_fit=85.0, core=67.0, summary=92.0, missed=53.0, noise=78.0
- Summary: 요약과 섹션 적합성은 양호하지만, 후보가 충분한데도 공급·정책·병해충이 각각 3건에 그쳤다. 공급 시황과 유통 운영 분석을 놓치고 일부 지역 실적·지원 기사가 핵심 또는 꼬리 자리를 차지해 선별 논리 보완이 필요하다.
- [major] underfill: 공급·정책·병해충 섹션 각 3건 편성 - 가용 후보가 충분한 세 섹션에서 최소 편성에 머물러 총 6개 슬롯이 비었다.
- [major] missed_candidate: [2026년 9월 5주] 주요 농산물 경락가 상승·하락 품목 - 쌈배추 145.8% 상승 등 전국 도매가격 신호를 담은 최상위 공급 후보를 누락했다.
- [moderate] weak_core: 단양군, 2026년 단양 마늘 우량종구 11.3톤 공급 완료 - 단일 군의 종구 보급 실적으로 전국 수급·시장 신호보다 핵심성이 낮다.
- [moderate] weak_core: 충남도 농축산국, 생성형 AI로 농업업무 시스템 직접 개발 - 지역 행정시스템 구축 사례로 법 개정·소득·통상 현안보다 정책 파급력이 작다.
- [moderate] weak_core: '3중고' K-농업…소득·기술·CPTPP 모두 '위기' - 경영비·농업소득·R&D·통상을 아우르는 전국 정책 현안인데 비핵심 처리됐다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: supply, policy, pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-2), policy(-2), pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=7%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
