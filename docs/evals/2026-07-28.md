## Daily Eval (2026-07-28)
- Overall: **69.30** (fail)
- Operational: **89.87**
- Reader quality: **76.10** (clear; penalty=13.8, cap=100.0, reasons=clear)
- Quality gate: **69.30** (needs_major_iteration, editorial_major_issue; editorial=70.8, operational=89.9)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=88.8, section_fit=100.0, core=89.1, commodity=98.1
- Briefing cards: 20 / Commodity cards: 40
- Sections: supply:5/5 raw=179, policy:5/5 raw=113, dist:5/5 raw=64, pest:5/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.20, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=3.15, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=7.7, commodity_weak=0.00, commodity_items=12, commodity_active_today=15, commodity_active_today_unlinked=3, commodity_coverage=0.36, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **70.80** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 70.80; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=72.0, section_fit=78.0, core=65.0, summary=89.0, missed=55.0, noise=65.0
- Summary: 20개 슬롯과 최신성, 요약 품질은 충족했지만 정책 핵심기사 선택과 중복 통제가 약하다. 정책 풀의 전국 단위 수급·재해지원·유통정책 후보를 놓치고 홍보성 할인 안내와 지역 점검을 핵심으로 올렸으며, 유통에는 가격 동향 기사가 섞였다. 병해충에서는 울진 혹명나방 동일 사건을 두 번 싣고 더 구체적인 탄저병 후보를 누락했다.
- [major] duplicate_story: 울진군, 혹명나방 피해 확산 대응…농업기술센터 전직원 예찰·공동방제 - 17번 카드와 같은 예찰·공동방제 사건을 출처만 바꿔 중복 게재했다.
- [major] missed_candidate: [아주초대석] 홍문표 aT사장 "농산물 수급 불안, 韓 농업의 취약한 구조" - 정책 풀 최고 점수의 전국 단위 수급구조 진단을 누락하고 약한 지역·할인 기사를 선택했다.
- [moderate] promotional_filler: 복날에 지갑 열자 '정부 30% 할인'으로 삼계탕 물가 방어하는 법 - 정부 기자단식 소비 안내 성격이 강하고 농정 핵심 의제나 집행 분석이 부족하다.
- [moderate] weak_core: 강원농업기술원, 폭염 대응 농업인 안전 현장지원 강화 - 지역 현장점검 중심 기사로 전국 수급·지원 정책 후보보다 핵심성이 낮다.
- [moderate] missed_candidate: 농산물 유통개혁 6000억 투입했지만…성과 검증·농협 역할 재정립 필요 - 스마트APC·온라인도매시장 성과를 다룬 전국 단위 유통정책 후보가 지역 점검과 가격 기사보다 강하다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=25%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
