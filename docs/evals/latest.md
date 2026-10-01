## Daily Eval (2026-09-23)
- Overall: **93.20** (warn)
- Operational: **96.61**
- Reader quality: **96.61** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **93.20** (needs_major_iteration, editorial_major_issue; editorial=73.3, operational=96.6)
- Scores: completeness=100.0, diversity=96.4, source=100.0, summary=100.0, freshness=100.0, retrieval=91.9, section_fit=91.7, core=85.0, commodity=99.0
- Briefing cards: 20 / Commodity cards: 23
- Sections: supply:5/5 raw=217, policy:5/5 raw=147, dist:5/5 raw=84, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.65, low_tier=0.10, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.11, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=6, commodity_active_today=16, commodity_active_today_unlinked=10, commodity_coverage=0.18, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.33, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **73.35** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 74.70; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=72.0, section_fit=76.0, core=70.0, summary=82.0, missed=67.0, noise=76.0
- Summary: 20건을 채웠고 요약도 대체로 유용하지만, 정책 섹션의 추석 차례상 기사 과잉 중복과 유통·병해충 섹션의 약한 후순위 카드가 품질을 낮춘다. 핵심 기사 지정도 일부 재조정이 필요하다.
- [major] duplicate_theme: 추석 차례상 비용 하락?...체감 경기는 '팍팍' [뉴스UP] - 정책 5건 중 4건이 추석 차례상 물가를 반복하며 수치도 조사 기준 설명 없이 충돌한다.
- [moderate] weak_core: 박정훈 식량정책실장, 사과 수급 현장 점검 - 구체적인 수급 수치나 조치가 없는 단순 현장 방문 기사다.
- [moderate] wrong_section: 거창군 농특산물, 전국 유통망 통한 판로 확대 - 전국 유통망 입점과 판매가격을 다룬 판로 기사로 dist 적합도가 더 높다.
- [moderate] promotional_filler: [국민의 기업] 배·포도 맛본 아세안 인플루언서, K과일 매력 알린다 - 팸투어 홍보 성격이 강하고 실제 계약·수출 물량 성과가 없다.
- [moderate] missed_candidate: 동계농협 ‘동계 밤’ 12년 연속 중국 수출 - 150t 규모의 구체적 수출 실적이 팸투어보다 유통·수출 운영 가치가 높다.

### Improvement Hints
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
