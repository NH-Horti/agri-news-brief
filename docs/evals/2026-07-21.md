## Daily Eval (2026-07-21)
- Overall: **88.49** (pass)
- Operational: **92.25**
- Reader quality: **90.75** (capped; penalty=1.5, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **88.49** (needs_iteration, editorial_major_issue; editorial=84.0, operational=92.2)
- Scores: completeness=92.8, diversity=94.1, source=71.1, summary=100.0, freshness=100.0, retrieval=87.5, section_fit=87.4, core=91.0, commodity=88.0
- Briefing cards: 18 / Commodity cards: 21
- Sections: supply:5/5 raw=201, policy:5/5 raw=114, dist:5/5 raw=85, pest:3/5 raw=41
- Metrics: title_unique=1.00, domain_diversity=0.94, low_tier=0.22, summary_presence=1.00, summary_numeric=0.67, fresh_72h=1.00, fit_avg=3.48, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=6, commodity_active_today=13, commodity_active_today_unlinked=7, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.83, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.95** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 84.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 97.5 (minimum_fallback)
- Components: article_selection=85.0, section_fit=82.0, core=80.0, summary=94.0, missed=78.0, noise=86.0
- Summary: 가격·수급, 온라인 도매시장, 벼 병해충 등 주요 축은 잡았지만 정책 코어에 기업 신품종 공급 PR성 기사가 들어가고, 공급·정책 일부 꼬리 카드가 더 강한 후보를 밀어낸 점이 큽니다. 특히 pest는 원자료가 충분한데 3장에 그쳐 일일 브리핑 완성도가 떨어집니다.
- [major] promotional_filler: 다산바이오, 제주 성산농협에 월동무 신품종 '무궁무진' 공급 - 기업의 종자 공급·시장 확대 성격이 강해 정책 코어로 부적절하다.
- [moderate] wrong_section: "벌 마늘 만 피해인가" 이경재 경남도의원, 저품위 마늘 지원 대상 확대 ... - 가격·생산 수급보다 지방의회 지원대상 확대 요구에 가까운 정책 기사다.
- [moderate] missed_candidate: '가난한 풍년' 배추 갈아엎는 농민 - 산지 가격 폭락과 폐기라는 강한 공급·농가 피해 신호인데 약한 꼬리 기사에 밀렸다.
- [moderate] noise: 식품업계 '릴레이 가격 인상'…먹거리 물가 더 오른다 - 가공식품 기업 가격 인상 중심으로 농업 정책 독자에게는 관련성이 간접적이다.
- [moderate] missed_candidate: 농축산물 안정적 공급...선제적 수급관리체계 재정립 - 농식품부 하반기 업무계획의 수급·유통 정책 축을 다루는 더 강한 전국 정책 후보가 보였다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 6%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
