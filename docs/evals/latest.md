## Daily Eval (2026-09-21)
- Overall: **86.00** (warn)
- Operational: **92.06**
- Reader quality: **90.56** (capped; penalty=1.5, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **86.00** (needs_major_iteration, editorial_major_issue; editorial=73.8, operational=92.1)
- Scores: completeness=92.8, diversity=94.2, source=71.1, summary=100.0, freshness=91.6, retrieval=90.6, section_fit=88.6, core=99.1, commodity=88.0
- Briefing cards: 18 / Commodity cards: 21
- Sections: supply:5/5 raw=301, policy:5/5 raw=204, dist:5/5 raw=93, pest:3/5 raw=35
- Metrics: title_unique=1.00, domain_diversity=0.83, low_tier=0.22, summary_presence=1.00, summary_numeric=0.78, fresh_72h=1.00, fit_avg=3.75, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=8, commodity_active_today=15, commodity_active_today_unlinked=7, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.88, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **73.75** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 74.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 97.5 (minimum_fallback)
- Components: article_selection=72.0, section_fit=84.0, core=70.0, summary=91.0, missed=60.0, noise=65.0
- Summary: 요약 품질과 유통 핵심 기사들은 양호하지만, 공급의 추석 물가 편중, 정책 핵심 선정 오류, 유통·병해충의 주제 중복이 크다. 병해충도 활용 가능한 후보가 있는데 3건에 그쳐 선택 로직 보완이 필요하다.
- [major] duplicate_theme: 추석 차례상 물가 5.1% 올랐다… 폭염에 채소류 급등 - 공급 5건 대부분이 추석 장바구니 물가를 반복해 정보 확장성이 낮다.
- [moderate] weak_core: 고깃값 오르고 과일은 내려, 추석 성수품 가격 '양극화' - 울산 지역 조사로 전국 독자 대상 핵심 기사로는 범위가 좁다.
- [moderate] promotional_filler: [추석 장보기 풍경 上] "많이 올랐어"… 가격 표 보고 집었다 놓았다 - 현장 반응 중심의 정성 기사로 수급 판단에 필요한 수치와 운영 정보가 부족하다.
- [moderate] wrong_section: [티조챗] "과일·채소 몇 개 담았는데 10만원"…공포의 추석 물가, 지원 ... - 정책보다 소비자 물가 풍경과 할인행사 소개가 중심이며 공급 기사들과도 겹친다.
- [major] missed_candidate: 농안법 개정안 시행… 마늘·양파 단체 "실질적 가격 안전망 구축하라" - 법 시행과 생산자 요구를 함께 다룬 직접적인 정책 현안이 물가성 기사보다 중요하다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 6%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
