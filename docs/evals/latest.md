## Daily Eval (2026-07-15)
- Overall: **92.87** (pass)
- Operational: **97.51**
- Reader quality: **97.51** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **92.87** (needs_major_iteration, editorial_major_issue; editorial=79.5, operational=97.5)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=98.5, freshness=100.0, retrieval=87.5, section_fit=97.2, core=100.0, commodity=96.1
- Briefing cards: 20 / Commodity cards: 15
- Sections: supply:5/5 raw=214, policy:5/5 raw=115, dist:5/5 raw=64, pest:5/5 raw=30
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.20, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=3.88, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=7, commodity_active_today=11, commodity_active_today_unlinked=4, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **79.45** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 79.50; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=78.0, core=76.0, summary=86.0, missed=77.0, noise=76.0
- Summary: 분량은 4개 섹션 모두 5건으로 충족했고 유통개혁, 축산 온라인경매, 제주 항공운송, 정부 먹거리 물가대책 등 핵심 축은 좋다. 다만 공급 섹션에 병해충성 산림 이슈가 들어가고, 정책·병해충에서 중복/홍보성/지역 행사성 카드가 강한 후보를 밀어낸 점이 크다. 특히 pest의 제품 홍보 기사를 core로 둔 것과 policy의 신선란 대책 중복, supply의 양파 완판 행사를 core로 둔 선택은 일일 농업 브리핑 기준으로 편집 품질을 낮춘다.
- [major] wrong_section: [전국톡톡] 폭염 속 소나무재선충병 26배 급증 - 소나무재선충병은 산림 병해충 이슈로 공급·수급 카드로 보기 어렵다.
- [moderate] weak_core: 양파 농가 시름 던다…김천시 공직자들, 햇 양파 7톤 '완판' - 지역 공직자 구매 행사 성격이 강해 공급 섹션 core로는 약하다.
- [major] promotional_filler: “하룻밤 새 번지던 흰가루병…한번 살포로 발생 뚝” - 특정 업체 신제품 효능을 홍보하는 내용이 강해 pest core로 부적절하다.
- [moderate] duplicate_story: 농식품부, 16일부터 신선란 할인 판매…수급 점검 - 정부 먹거리 물가 안정·신선란 공급 확대 카드와 사실상 같은 대책을 반복한다.
- [moderate] bad_summary: 농식품부, 16일부터 신선란 할인 판매…수급 점검 - 요약이 기사 제목과 매체명만 반복해 독자에게 추가 정보를 주지 않는다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
