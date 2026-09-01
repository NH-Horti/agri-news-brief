## Daily Eval (2026-09-02)
- Overall: **87.45** (pass)
- Operational: **95.45**
- Reader quality: **95.45** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **87.45** (needs_major_iteration, editorial_major_issue; editorial=67.0, operational=95.5)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=92.5, section_fit=100.0, core=99.5, commodity=36.0
- Briefing cards: 20 / Commodity cards: 27
- Sections: supply:5/5 raw=309, policy:5/5 raw=192, dist:5/5 raw=62, pest:5/5 raw=35
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.20, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=3.40, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=3, commodity_active_today=14, commodity_active_today_unlinked=11, commodity_coverage=0.09, commodity_strict_link=0.33, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=1.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **66.95** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 68.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=4, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=68.0, section_fit=70.0, core=64.0, summary=89.0, missed=52.0, noise=55.0
- Summary: 형식과 분량은 충족했지만 강한 후보를 놓치고 정책·중국산 배추 이슈를 중복 편성했다. 공급·유통의 홍보성 꼬리와 병해충 섹션의 예산 기사가 품질을 낮춘다.
- [major] missed_candidate: [추석 과일 시장 점검] ‘배’ 작황 양호…폭염으로 ‘대과’ 비중 줄듯 - 작황·규격·가격 전망을 함께 담은 최고 적합 후보가 빠졌다.
- [major] duplicate_theme: 정부 ‘추석 물가 안정대책’ 발표…공급량도 할인폭도 ‘역대 최대’ - 첫 카드와 동일한 추석 성수품 공급·할인 대책이다.
- [moderate] duplicate_theme: [2027 예산안]농식품부, '역대 최대' 22조2215억원… - 기본소득·직불금 및 신규사업 기사와 같은 예산안을 반복한다.
- [major] duplicate_story: 중국산 배추, 정말 괜찮나요?...불안감 '증폭'에 특단의 조치 - 가락시장·판매업소 점검 카드와 같은 중국산 배추 안전성 대응이다.
- [moderate] promotional_filler: 이마트, '오더투홈' 절임 배추 사전예약 - 단일 유통업체 예약판매 홍보에 치우치며 공급 동향 정보가 약하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
