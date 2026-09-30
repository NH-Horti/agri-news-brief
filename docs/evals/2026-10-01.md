## Daily Eval (2026-10-01)
- Overall: **86.58** (warn)
- Operational: **93.26**
- Reader quality: **89.78** (capped; penalty=3.5, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **86.58** (needs_major_iteration, editorial_major_issue; editorial=74.2, operational=93.3)
- Scores: completeness=92.8, diversity=97.6, source=100.0, summary=100.0, freshness=100.0, retrieval=78.1, section_fit=100.0, core=100.0, commodity=87.0
- Briefing cards: 15 / Commodity cards: 21
- Sections: supply:4/5 raw=199, policy:5/5 raw=67, dist:4/5 raw=48, pest:2/2 raw=7
- Metrics: title_unique=1.00, domain_diversity=0.67, low_tier=0.13, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=2.92, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.3, commodity_weak=0.00, commodity_items=6, commodity_active_today=12, commodity_active_today_unlinked=6, commodity_coverage=0.18, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=1.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **74.20** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 74.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, section_count_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 83.5 (underfilled)
- Components: article_selection=75.0, section_fit=79.0, core=72.0, summary=87.0, missed=65.0, noise=64.0
- Summary: 요약 품질은 안정적이지만 강한 정책·재해 후보를 놓치고 홍보성·지역 행사성 카드로 채웠다. supply·dist는 후보가 충분한데도 4건에 그쳤고, 핵심 카드 우선순위도 일부 부적절하다.
- [major] missed_candidate: 위상 높인 농산물 수급조절위 8기 닻 올려 - 법정위원회 전환과 과수 수급관리 확대를 다룬 당일 최상위 정책 후보가 누락됐다.
- [moderate] weak_core: 상주시, 샤인머스캣 가격 하락에 '품질 승부'…현장지도 강화 - 지역 현장지도 중심으로 파급력이 제한돼 supply core로 약하다.
- [moderate] weak_core: 2025년도 면적당 농산물 소득 7.7% 줄었다 - 전국 5300농가 조사와 경영비 상승을 담아 현재 비핵심 카드보다 정책 중요도가 높다.
- [moderate] promotional_filler: 수확 뒤 과수 수세 회복···조비, 감사비료 2종 제안 - 특정 업체 제품 제안이 중심인 상업성 콘텐츠다.
- [moderate] promotional_filler: 추석 농축산물 할인, 장바구니 너머 농가의 이야기도 들어보니 - 정책 효과나 수치보다 정부 할인정책 홍보와 체험담에 치우쳤다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1), dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=13%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
