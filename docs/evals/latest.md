## Daily Eval (2026-09-21)
- Overall: **84.87** (warn)
- Operational: **91.62**
- Reader quality: **89.37** (capped; penalty=2.2, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **84.87** (needs_major_iteration, editorial_major_issue; editorial=74.0, operational=91.6)
- Scores: completeness=89.2, diversity=93.2, source=65.9, summary=100.0, freshness=94.2, retrieval=90.6, section_fit=100.0, core=96.7, commodity=88.0
- Briefing cards: 17 / Commodity cards: 21
- Sections: supply:4/5 raw=302, policy:5/5 raw=203, dist:5/5 raw=93, pest:3/5 raw=35
- Metrics: title_unique=1.00, domain_diversity=0.88, low_tier=0.24, summary_presence=1.00, summary_numeric=0.82, fresh_72h=1.00, fit_avg=3.98, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=8, commodity_active_today=15, commodity_active_today_unlinked=7, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.88, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **74.00** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 75.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 95.5 (soft_fallback)
- Components: article_selection=73.0, section_fit=77.0, core=69.0, summary=91.0, missed=61.0, noise=76.0
- Summary: 요약은 명료하지만 정책의 약한 핵심 선정, 공급·정책의 추석 물가 반복, 유통 토론회 중복, 병해충 미충원이 품질을 낮춘다. 원시 후보에 더 강한 정책·방제 기사가 있어 재선정이 필요하다.
- [major] weak_core: 대전·세종·충남 "가족과 함께 편안한 추석을"…연휴 분야별 대책 마련 - 농업정책보다 지방정부 연휴 종합대책 성격이 강해 핵심 카드로 약하다.
- [major] missed_candidate: 농안법 개정안 시행… 마늘·양파 단체 "실질적 가격 안전망 구축하라" - 법 시행과 생산자 요구를 다룬 강한 전국 정책 후보가 지방 연휴대책보다 우선이다.
- [moderate] duplicate_theme: [티조챗] "과일·채소 몇 개 담았는데 10만원"…공포의 추석 물가, 지원 ... - 공급 섹션의 추석 차례상 가격 기사들과 주제와 수치가 크게 겹친다.
- [moderate] wrong_section: 수확 끝난 과수원, 내년 농사 성패는 '감사비료'에 달렸다 - 수급·가격 동향이 아니라 재배관리 정보여서 공급 섹션 적합도가 낮다.
- [moderate] duplicate_theme: [918 농산물 유통구조 혁신 토론회] 농산물 제값 '1차 가격' 확보 중요·... - 같은 유통구조 토론회의 가격결정력 논의를 앞 카드와 반복한다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1), pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
