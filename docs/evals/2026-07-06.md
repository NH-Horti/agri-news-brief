## Daily Eval (2026-07-06)
- Overall: **93.40** (pass)
- Operational: **94.21**
- Reader quality: **94.21** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **93.40** (needs_iteration, editorial_acceptance_gate_failed; editorial=84.8, operational=94.2)
- Scores: completeness=100.0, diversity=92.9, source=100.0, summary=89.5, freshness=90.0, retrieval=89.4, section_fit=95.8, core=100.0, commodity=98.5
- Briefing cards: 20 / Commodity cards: 26
- Sections: supply:5/5 raw=255, policy:5/5 raw=138, dist:5/5 raw=100, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.15, summary_presence=1.00, summary_numeric=0.65, fresh_72h=1.00, fit_avg=3.99, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=11, commodity_active_today=16, commodity_active_today_unlinked=5, commodity_coverage=0.33, commodity_strict_link=0.91, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.36, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.75** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 85.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, operational_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=87.0, section_fit=90.0, core=85.0, summary=78.0, missed=80.0, noise=88.0
- Summary: 전체 4개 섹션 모두 5건을 채워 기본 완성도는 높고, 수급·정책 핵심 일부는 적절하다. 다만 pest에서 가장 시의성 있고 수치가 뚜렷한 충북 과수화상병 소강·재확산 대비 기사를 놓쳤고, dist도 더 강한 산지유통·경매 운영 후보를 두고 지역 첫 출하성 카드가 들어갔다. policy에는 시장 가격 폭락 항의성 기사가 섞였고, 일부 요약은 본문 조각·사진 설명이 남아 독자 효용을 낮춘다.
- [moderate] missed_candidate: 폭염에 충북 과수화상병 소강 국면 - 피해 51곳·21.68㏊, 예찰 일정 등 핵심 수치가 있는 최상위 병해충 후보를 미선정했다.
- [moderate] weak_core: 과수화상병 조기 신고가 피해 줄인다 - 과수화상병 주제는 맞지만 최신 발생 규모와 재확산 리스크를 담은 raw 상위 후보보다 코어성이 약하다.
- [moderate] missed_candidate: 햇마늘 경매 개시…“농가 제값받기 최선” - 상품 평균 경락가, 출하예약제, 거래량 전망이 있는 강한 유통 운영 기사인데 미선정됐다.
- [moderate] missed_candidate: 경북지역 조합공동사업법인, 농산물 판매확대로 농가소득 증대 앞장 - 산지유통 조직·컨설팅·연합사업 강화 내용이 구체적인데 지역 홍보성 카드에 밀렸다.
- [moderate] wrong_section: 생산비도 못 건지는 양배추 값...밭 갈아엎은 농민들 - 정책 요구가 언급되지만 본질은 양배추 가격 폭락 현장 기사로 supply 성격이 더 강하다.

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
