## Daily Eval (2026-07-07)
- Overall: **92.00** (pass)
- Operational: **95.10**
- Reader quality: **92.85** (capped; penalty=2.3, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **92.00** (needs_iteration, editorial_acceptance_gate_failed; editorial=84.6, operational=95.1)
- Scores: completeness=96.4, diversity=95.2, source=75.8, summary=98.4, freshness=100.0, retrieval=87.5, section_fit=100.0, core=100.0, commodity=89.4
- Briefing cards: 19 / Commodity cards: 44
- Sections: supply:5/5 raw=250, policy:5/5 raw=109, dist:5/5 raw=84, pest:4/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.84, low_tier=0.21, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=4.05, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=11, commodity_active_today=14, commodity_active_today_unlinked=3, commodity_coverage=0.33, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.73, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.60** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 85.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=84.0, section_fit=86.0, core=88.0, summary=86.0, missed=80.0, noise=82.0
- Summary: 전반적으로 핵심 수급·유통·병해충 이슈는 잡았지만, 충분한 후보가 있었는데도 일부 섹션에 지역 행사·사진성 filler가 들어갔고 pest는 4건으로 underfill됐다. dist와 supply의 꼬리 카드 품질, pest의 일반 농사메모 선택, policy의 더 강한 전국 정책 후보 누락이 점수를 낮춘다.
- [moderate] underfill: pest 섹션 4건 편성 - 원천 후보가 53건이고 고추 병해충·오이 예찰 등 추가 가능한 후보가 있었는데 5건을 채우지 못했다.
- [moderate] noise: [주간 농사 메모]고온 시 과수 햇볕 뎀 피해 주의 - 병해충 기사라기보다 범용 주간 영농 메모라 pest 섹션의 긴급성·구체성이 약하다.
- [moderate] promotional_filler: 분주한 햇 마늘 경매 현장 - 단문 사진 기사로 유통 운영·가격·물량 정보가 거의 없어 dist 카드로 정보 가치가 낮다.
- [moderate] promotional_filler: 고랭지 채소 출하철 맞아 대관령 공판사업소 개장 - 초매식·공판장 개장 중심의 지역 행사성 기사이며 후보 풀 대비 수급 분석성이 약하다.
- [moderate] missed_candidate: [미리보는 하반기 경제성장전략] 유가 꺾여도 3%대 물가…정부, '민생물...' - 전국 단위 농축수산물 할인·민생물가 정책 후보가 있는데 지역 CPI 카드가 우선됐다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
