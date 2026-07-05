## Daily Eval (2026-07-06)
- Overall: **84.50** (warn)
- Operational: **97.01**
- Reader quality: **90.00** (capped; penalty=4.7, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **84.50** (needs_iteration, editorial_major_issue; editorial=81.0, operational=97.0)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=90.0, retrieval=89.4, section_fit=97.2, core=100.0, commodity=100.0
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=255, policy:5/5 raw=138, dist:5/5 raw=100, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.24, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=12, commodity_active_today=15, commodity_active_today_unlinked=3, commodity_coverage=0.36, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.42, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **81.00** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 82.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=84.0, core=78.0, summary=88.0, missed=74.0, noise=80.0
- Summary: 분량은 4개 섹션 모두 5건으로 충족했고 주요 수급·유통·과수화상병 이슈도 상당수 잡았다. 다만 정책 섹션에서 전국 단위 핵심 후보를 놓치고 지역 지원사업을 코어로 올린 점, 유통과 병해충 섹션의 중복 기사, 공급 섹션의 지역 세일즈·수출성 기사 배치가 품질을 낮춘다. 일일 브리핑으로는 사용 가능하지만 기사 선택 우선순위와 중복 제어가 더 필요하다.
- [major] weak_core: 예산군, 과수저장시설 신선도유지제 지원사업 추진 - 지역 단위 지원사업을 정책 코어로 세운 것은 전국 독자용 정책 중요도에 비해 약하다.
- [major] missed_candidate: 농가당 26만원…쥐꼬리 ‘FTA직불금’ - 정책 raw 최상위권의 전국 제도 실효성 이슈인데 선정되지 않았다.
- [moderate] missed_candidate: "농축산물 할인에 '3000억' 투입" 파격 카드...먹거리 물가 잡힐까 - 먹거리 물가 대응 예산은 농업 정책·가격 안정 독자 관심도가 높은 후보였다.
- [moderate] duplicate_story: "농산물 유통역량 강화"···희망재단 '농업인 현장컨설팅' - 가락시장 현장컨설팅 기사로 12번 카드와 사실상 같은 행사와 메시지다.
- [moderate] missed_candidate: 경북지역 조합공동사업법인, 농산물 판매확대로 농가소득 증대 앞장 - 산지유통 경쟁력·판매 확대 논의로 중복 컨설팅 카드보다 유통 섹션 적합도가 높다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
