## Daily Eval (2026-09-18)
- Overall: **89.27** (warn)
- Operational: **95.27**
- Reader quality: **94.52** (capped; penalty=0.8, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **89.27** (needs_major_iteration, editorial_major_issue; editorial=71.0, operational=95.3)
- Scores: completeness=96.4, diversity=95.1, source=100.0, summary=100.0, freshness=100.0, retrieval=85.1, section_fit=100.0, core=96.6, commodity=88.0
- Briefing cards: 19 / Commodity cards: 26
- Sections: supply:4/5 raw=265, policy:5/5 raw=102, dist:5/5 raw=80, pest:5/5 raw=23
- Metrics: title_unique=1.00, domain_diversity=0.63, low_tier=0.11, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.31, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=6, commodity_active_today=14, commodity_active_today_unlinked=8, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.83, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **71.00** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 72.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=68.0, section_fit=78.0, core=66.0, summary=91.0, missed=57.0, noise=69.0
- Summary: 형식과 요약은 안정적이지만, 강한 수급·정책·수출 후보를 두고 현장점검·캠페인·기관행사성 기사를 다수 선택했다. 특히 정책과 유통의 핵심 선정, pest의 범위 정리가 필요하다.
- [major] missed_candidate: ‘농산물가격안정제’ 마늘·양파 첫 적용 앞두고…‘기준 가격’ 공방 - 전국적 제도 변화와 농가 쟁점을 다룬 최상위 정책 후보가 빠졌다.
- [major] missed_candidate: 한국포도협회, 추석 앞두고 샤인머스켓 하품 230톤 시장 격리 - 출하 증가와 가격 방어에 직접 연결되는 구체적 수급조치다.
- [moderate] missed_candidate: ‘영암배’ 400만불 수출 정조준 - 실제 수출 확대와 해외 판로라는 강한 유통 후보가 누락됐다.
- [moderate] promotional_filler: 충북농협, 우박 피해 사과 판로 지원 ‘착한소비 캠페인’ - 1440봉 일회성 판매행사로 전국 수급 정보 가치가 낮다.
- [moderate] duplicate_theme: 농협 대전본부, '추석 전 농산물 수급· 가격 점검' 실시 - 성수품 공급대책 기사들과 주제가 겹치고 실질 조치도 약하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
