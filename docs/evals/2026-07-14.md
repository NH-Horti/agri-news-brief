## Daily Eval (2026-07-14)
- Overall: **86.00** (pass)
- Operational: **97.19**
- Reader quality: **90.00** (capped; penalty=4.7, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **86.00** (needs_iteration, editorial_major_issue; editorial=82.0, operational=97.2)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=85.0, section_fit=100.0, core=88.5, commodity=92.0
- Briefing cards: 20 / Commodity cards: 29
- Sections: supply:5/5 raw=177, policy:5/5 raw=169, dist:5/5 raw=57, pest:5/5 raw=46
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.15, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.85, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=9, commodity_active_today=11, commodity_active_today_unlinked=2, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 82.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=85.0, core=80.0, summary=90.0, missed=75.0, noise=80.0
- Summary: 분량과 신선도는 충족했지만, 정책 섹션의 동일 농협 2200억원 지원 중복과 유통 섹션의 기고성·홍보성 카드가 데일리 브리핑 품질을 크게 낮췄다. 수급·유통·병해충 모두 더 강한 원자료 후보가 보였는데 일부 지역 행사·교육·반복 방제 기사로 채워졌다. 요약 자체는 대체로 유용하지만 기사 선택과 코어 지정의 엄격성이 부족하다.
- [major] duplicate_story: 농협, 2200억원 규모 ‘힘내라 우리 농업’ 프로젝트로 농가 부담 낮춘... - 6번 농협 2200억원 지원 기사와 같은 사안을 반복해 정책 슬롯 하나를 낭비했다.
- [major] missed_candidate: 미국산 신선란 가격 인하…이마트서 30구 5890원→4980원 - 정책 원자료 최상위권의 정부 수급안정·계란 수입·할인지원 이슈를 누락했다.
- [moderate] promotional_filler: [기고] 고창 선운산 수박, 명품은 하루아침에 만들어지지 않는다 - 기고문 성격의 지역 브랜드 홍보로 유통·물류·판로 운영 정보가 약하다.
- [moderate] duplicate_story: 영주 여름 사과 본격 출하 …유통 경쟁력 강화 - 영주 여름사과 첫 출하가 수급과 유통 섹션에 중복 배치됐다.
- [moderate] weak_core: 감귤 경매사한테서 듣는 감귤 출하전략 - 농가 교육 기사로 유통 코어로 삼기에는 당일 시장운영·물류·수출 영향이 제한적이다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
