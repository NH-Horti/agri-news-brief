## Daily Eval (2026-07-01)
- Overall: **81.90** (warn)
- Operational: **88.20**
- Reader quality: **83.30** (capped; penalty=4.9, cap=88.0, reasons=story_duplicate)
- Quality gate: **81.90** (needs_major_iteration, editorial_below_target_bounded_penalty; editorial=81.0, operational=88.2)
- Scores: completeness=100.0, diversity=85.0, summary=100.0, freshness=100.0, retrieval=72.4, section_fit=100.0, core=78.7, commodity=92.0
- Briefing cards: 20 / Commodity cards: 23
- Sections: supply:5/5 raw=203, policy:5/5 raw=111, dist:5/5 raw=52, pest:5/5 raw=12
- Metrics: title_unique=0.95, domain_diversity=0.55, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.75, false_positive=0.00, hard_reader_issues=0, weak_core=0.43, editorial_penalty=0.5, commodity_weak=0.00, commodity_items=6, commodity_active_today=14, commodity_active_today_unlinked=8, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **81.00** (target 95, needs_major_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=82.0, core=76.0, summary=70.0, missed=74.0, noise=68.0
- Summary: 분량과 신선도는 충족했지만, 정책 섹션의 동일 기사 중복, 공급 섹션의 외식 프랜차이즈 가격 기사 편입, 일부 약한 코어 지정과 오염된 요약 때문에 95점권은 어렵다. 주요 수급·정책·유통 이슈는 대체로 잡았으나, 몇몇 더 구체적인 물류·수급 후보를 약한 로컬/회의성 기사보다 우선했어야 한다.
- [major] duplicate: 계절관세 철폐…미국산 감자 공세에 농가 ‘비상’ - 동일 기사와 요약이 8·9번에 중복 배치돼 정책 슬롯 하나를 낭비했다.
- [major] off_scope: 중량 줄이더니 가격도…굽네치킨, 일부 사이드 메뉴 인상 - 외식 프랜차이즈 사이드 메뉴 가격 인상으로 원예 수급·산지 생산 기사와 거리가 멀다.
- [medium] weak_core: 고성군 밤나무병해충 무인항공기방제 13일부터 40일간 시행 - 지역 방제 일정·총회성 기사인데 코어로 지정됐다.
- [medium] missed_opportunity: 제주 첫 스마트공동물류센터 완공…‘물류비 절감’ - 구체적인 물류 인프라 완공 기사인데 회의·지원성 기사보다 독자 효용이 높다.
- [major] summary_quality: 한농연 “농산물 가격 안정의 해법은 수입 아닌 ‘국내 생산 기반’에” - TTS·스크랩·수정시각 등 원문 잡음이 요약에 그대로 남아 있다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 동일 사건이 브리핑 안에서 반복 노출됐습니다 (비율 5%). 같은 지역·숫자·지원/가격 이벤트가 겹치는 기사는 한 섹션에만 남기세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
