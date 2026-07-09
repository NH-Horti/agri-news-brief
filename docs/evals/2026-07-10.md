## Daily Eval (2026-07-10)
- Overall: **65.45** (fail)
- Operational: **98.64**
- Reader quality: **98.64** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **65.45** (needs_major_iteration, editorial_blocking_issue; editorial=65.5, operational=98.6)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=99.2, commodity=94.9
- Briefing cards: 20 / Commodity cards: 53
- Sections: supply:5/5 raw=188, policy:5/5 raw=141, dist:5/5 raw=84, pest:5/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.85, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.18, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=5, commodity_active_today=15, commodity_active_today_unlinked=10, commodity_coverage=0.15, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.60, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **65.45** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 66.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=3, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=60.0, section_fit=62.0, core=78.0, summary=82.0, missed=55.0, noise=50.0
- Summary: 분량은 4개 섹션 모두 5건으로 채웠지만, 원문 후보풀이 충분한 날치고는 중복·오배치·잡음이 많다. 양파 수급안정 기사와 도매시장 TF, 온라인도매시장 물류센터가 여러 섹션에서 반복됐고, pest에는 완전한 오프토픽 프랜차이즈 홍보성 기사가 들어갔다. 핵심 기사 일부는 괜찮지만 정책·병해충 섹션의 더 강한 후보를 놓쳐 일일 브리핑으로는 수정이 필요하다.
- [blocking] off_topic: 나나방콕, 가맹점 자동 칼질기계 도입비 전액 지원 - 프랜차이즈 주방장비 지원 PR로 병해충·농업 현안과 무관하다.
- [major] duplicate_story: 강화군, " 탄저병 ·역병 확산" 비상…'노지 고추' 현장관리 강화 - 16번 강화군 고추 탄저병 기사와 같은 사안이다.
- [major] duplicate_theme: 농협·정부·지자체 전방위 대책으로 양파값 두 달 만에 80% 회복 - 공급 섹션 핵심 양파 기사와 8번 정책 기사까지 같은 보도자료성 내용이 반복된다.
- [moderate] wrong_section: 장맛비 끝나면 채소값 오르나…산지 출하 감소에 가격 상승 '조짐' - 정책 결정이나 제도보다 산지 출하·가격 전망 기사에 가깝다.
- [moderate] wrong_section: 농식품부·aT, '거점물류센터 시범사업 협의체' 첫 회의 - 온라인도매시장 물류망 운영 기사로 dist 섹션 적합도가 더 높고 dist에서도 같은 이야기가 반복된다.

### Improvement Hints
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
