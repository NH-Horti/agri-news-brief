## Daily Eval (2026-10-07)
- Overall: **68.77** (fail)
- Operational: **84.77**
- Reader quality: **76.77** (capped; penalty=8.0, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **68.77** (needs_major_iteration, editorial_major_issue; editorial=68.1, operational=84.8)
- Scores: completeness=92.8, diversity=94.2, source=71.1, summary=100.0, freshness=100.0, retrieval=74.8, section_fit=90.7, core=85.0, commodity=91.9
- Briefing cards: 18 / Commodity cards: 12
- Sections: supply:5/5 raw=208, policy:5/5 raw=55, dist:5/5 raw=46, pest:3/5 raw=10
- Metrics: title_unique=1.00, domain_diversity=0.72, low_tier=0.22, summary_presence=1.00, summary_numeric=0.83, fresh_72h=1.00, fit_avg=4.57, false_positive=0.06, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=5, commodity_active_today=11, commodity_active_today_unlinked=6, commodity_coverage=0.15, commodity_strict_link=0.80, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.60, semantic_penalty=6.7


### Editorial Shadow Eval
- Editorial: **68.10** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 69.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=4, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, no_section_underfill)
- Section count gate: 97.5 (minimum_fallback)
- Components: article_selection=61.0, section_fit=66.0, core=79.0, summary=89.0, missed=54.0, noise=57.0
- Summary: 정책과 핵심 유통 기사는 대체로 유용하지만, 공급의 관광성 축제와 식생활 기사, 유통의 수상 기사, 병해충의 가격 기사·업체 제품성 콘텐츠가 품질을 크게 떨어뜨렸다. 원문 풀에 더 강한 물가·도매시장 시설 후보가 있었고 병해충은 3건에 그쳤다.
- [moderate] promotional_filler: ‘인삼보다 낫다’던 가을 무 …목이 칼칼한 환절기엔 이렇게 드세요 - 수급·생산 정보보다 제철 식재료와 조리법에 치우친 생활성 콘텐츠다.
- [major] missed_candidate: 9월 농축산물 물가 1.0% 하락…농식품부, 김장채소 생육관리 강화 - 물가, 배추·무 생육, 공급 안정 대책을 함께 담아 현재 선택된 비핵심 기사보다 훨씬 강하다.
- [major] promotional_filler: 신정호 경남 진주금산농협 조합장 ‘새로운 농협 조합장상’ 수상 - 유통 성과의 구체성이 부족한 인물 수상 홍보 기사다.
- [major] missed_candidate: 서울시, 강서시장 상품화 시설 건립 - 보관·소분·포장 일원화라는 구체적인 도매시장 운영 개선 기사인데 누락됐다.
- [major] wrong_section: 청송 시나노골드 상1 평균가 5만8801원…지난해보다 하락 - 핵심은 생산 증가와 공판장 가격 하락이며 병해충은 피해가 적었다는 배경에 불과하다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 6%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 6%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
