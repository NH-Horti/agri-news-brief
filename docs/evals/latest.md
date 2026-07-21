## Daily Eval (2026-07-22)
- Overall: **80.16** (warn)
- Operational: **91.91**
- Reader quality: **83.71** (capped; penalty=8.2, cap=90.0, reasons=pest_theme_duplicate, preferred_slot_underfill)
- Quality gate: **80.16** (needs_major_iteration, editorial_major_issue; editorial=78.8, operational=91.9)
- Scores: completeness=92.8, diversity=94.1, source=71.1, summary=96.7, freshness=100.0, retrieval=90.0, section_fit=100.0, core=88.9, commodity=88.0
- Briefing cards: 18 / Commodity cards: 21
- Sections: supply:5/5 raw=172, policy:5/5 raw=92, dist:4/5 raw=55, pest:4/5 raw=47
- Metrics: title_unique=1.00, domain_diversity=0.78, low_tier=0.22, summary_presence=1.00, summary_numeric=0.67, fresh_72h=1.00, fit_avg=4.98, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.7, commodity_weak=0.00, commodity_items=8, commodity_active_today=12, commodity_active_today_unlinked=4, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.88, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **78.80** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 81.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 96.0 (soft_fallback)
- Components: article_selection=80.0, section_fit=84.0, core=78.0, summary=82.0, missed=70.0, noise=78.0
- Summary: 전체적으로 주요 가격·수급 이슈는 일부 잘 잡았지만, 정책·유통·병해충에서 눈에 띄는 상위 후보를 놓치고 약한 지역 행사성·점검성 기사로 채운 부분이 큽니다. 특히 유통과 병해충은 원천 후보가 충분한데도 4개로 그쳐 일일 브리핑 완성도가 떨어졌고, 정책 섹션은 할당관세 분석 같은 당일 핵심 후보를 누락했습니다. 공급 섹션은 대체로 적합하나 유사한 광주·전남 가격 기사 중복감과 일부 요약 품질 문제가 있습니다.
- [major] missed_candidate: 할당관세에 수천억 쏟아붓지만… 물가 안정 ‘제한적’ 국내 생산기반 ‘위축’ - 정책 후보 중 가장 강한 당일 핵심 기사인데 누락됐고, 스쿨팜·친환경 직불금 기사보다 정책 중요도가 높다.
- [moderate] promotional_filler: 농협, 제주형 스쿨팜 확대 추진 - 지역 교육 프로그램 확대 소식으로 농정·수급 정책 브리핑의 우선순위가 낮고 원문도 종합 뉴스 묶음 성격이다.
- [moderate] underfill: 유통 섹션 4개 편성 - 유통 후보가 55개로 충분한데 목표 5개를 채우지 못했다.
- [moderate] weak_core: 농협경남본부, 공판장 안전관리· 농산물 판매 확대 점검 - 공판장 캠페인·결의대회 성격이 강해 유통 섹션 핵심 카드로는 약하다.
- [moderate] underfill: 병해충 섹션 4개 편성 - 병해충 후보가 47개로 충분한데 5개 목표를 채우지 못했다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1), pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=11%, pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
