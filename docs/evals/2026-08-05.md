## Daily Eval (2026-08-05)
- Overall: **76.59** (warn)
- Operational: **93.41**
- Reader quality: **83.07** (capped; penalty=10.3, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **76.59** (needs_major_iteration, editorial_major_issue; editorial=71.1, operational=93.4)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=83.0, section_fit=83.3, core=91.3, commodity=88.0
- Briefing cards: 20 / Commodity cards: 49
- Sections: supply:5/5 raw=282, policy:5/5 raw=211, dist:5/5 raw=62, pest:5/5 raw=20
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.20, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=3.43, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=1.3, commodity_weak=0.00, commodity_items=10, commodity_active_today=16, commodity_active_today_unlinked=6, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.90, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **71.10** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 73.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=70.0, section_fit=72.0, core=66.0, summary=91.0, missed=65.0, noise=62.0
- Summary: 분량과 요약은 충실하지만 정책 중복, 영천 기사 재사용, 약한 유통 핵심 선정, 병해충 섹션의 기상·행사성 채움으로 선택 품질이 낮다.
- [major] duplicate_story: 영천 여름 과일 출하 '순항'… / 영천 여름 과일 출하 본격화… - 같은 영천시장 공판장 점검 보도자료를 두 섹션에서 반복했다.
- [major] duplicate_theme: 7월 소비자물가 2.8%↑…석유류 안정에 2%대 복귀(종합2보) - 정책 5건 중 여러 건이 동일한 7월 물가 발표와 추석 대책을 반복한다.
- [moderate] missed_candidate: 7월 농축산물 물가 0.5%↑…농식품부 "할인 지원, 할당 관세로 물가 관리... - 원시 후보 중 농축산물 수치와 농식품부 조치를 가장 직접적으로 다룬 상위 후보를 누락했다.
- [major] weak_core: 영천 여름 과일 출하 본격화… 도매시장·공판장 거래 활기 - 지역 단체장의 현장 방문 성격이 강해 유통 핵심 기사로 약하다. 핵심에서 강등해야 한다.
- [moderate] missed_candidate: 서울청과, 출하기반 보전사업 2억4200만원 대대적 지원… - 378개 출하처의 포장·운송비 보전이라는 구체적 유통 운영 기사보다 지역 점검성 기사를 우선했다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, dist_weak_ops=5%, pest_theme_duplicate=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 10%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
