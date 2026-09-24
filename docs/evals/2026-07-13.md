## Daily Eval (2026-07-13)
- Overall: **89.92** (pass)
- Operational: **94.62**
- Reader quality: **93.87** (capped; penalty=0.8, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **89.92** (needs_iteration, editorial_major_issue; editorial=82.2, operational=94.6)
- Scores: completeness=96.4, diversity=98.2, source=96.8, summary=95.4, freshness=93.8, retrieval=90.6, section_fit=96.9, core=99.7, commodity=90.0
- Briefing cards: 19 / Commodity cards: 40
- Sections: supply:4/5 raw=294, policy:5/5 raw=147, dist:5/5 raw=91, pest:5/5 raw=50
- Metrics: title_unique=1.00, domain_diversity=0.68, low_tier=0.16, summary_presence=1.00, summary_numeric=0.42, fresh_72h=1.00, fit_avg=4.17, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=7, commodity_active_today=17, commodity_active_today_unlinked=10, commodity_coverage=0.21, commodity_strict_link=0.86, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.71, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.20** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 83.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=84.0, section_fit=87.0, core=81.0, summary=78.0, missed=79.0, noise=84.0
- Summary: 전반적으로 주요 섹션은 채웠고 유통·병해충 일부 핵심은 적절하지만, 원자료에 더 강한 전국 단위·운영성 기사가 보이는데도 약한 코어와 넓은 주제의 보충 카드가 섞였다. 특히 supply는 후보가 충분한데 4장에 그쳤고, policy의 주간 일정 코어 지정과 supply의 히트플레이션 기사, dist의 양파 가격 기사 배치는 편집 품질을 낮춘다. 일부 요약은 유료 구독 문구와 잘린 문장이 섞여 독자 효용이 떨어진다.
- [moderate] underfill: supply section - 원자료가 294건으로 충분한데 5장 목표 중 4장만 선정됐다.
- [major] missed_candidate: 정부·농협, 수급 대책 빛났다… 양파 경락값 완연한 회복세 - 양파 경락값 회복과 정책·농협 대책을 수치로 다룬 더 강한 공급 핵심 기사다.
- [major] weak_core: [정부 주요 일정] 경제·사회부처 주간 일정 (7월 13일 ~ 7월 17일) - 일정표는 농정 기사성이 약해 policy 코어로 부적합하다.
- [moderate] missed_candidate: 상추·수박·달걀 값 한달새 10%↑… 밥상물가 야금야금 오른다 - 정부 수급관리의 효과와 한계를 다룬 전국 단위 물가·정책 기사인데 빠졌다.
- [moderate] weak_core: 펄펄 끓는 여름 날씨보다 무서운 '히트플레이션' 습격 - 농산물 수급 직접성이 낮은 일반 물가 해설이고 요약도 구독 문구가 섞였다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
