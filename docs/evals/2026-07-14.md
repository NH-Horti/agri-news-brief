## Daily Eval (2026-07-14)
- Overall: **85.57** (pass)
- Operational: **96.80**
- Reader quality: **90.00** (capped; penalty=4.7, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **85.57** (needs_iteration, editorial_major_issue; editorial=80.3, operational=96.8)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=97.0, freshness=100.0, retrieval=85.0, section_fit=100.0, core=88.5, commodity=93.8
- Briefing cards: 20 / Commodity cards: 28
- Sections: supply:5/5 raw=178, policy:5/5 raw=174, dist:5/5 raw=57, pest:5/5 raw=46
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.15, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.85, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=8, commodity_active_today=10, commodity_active_today_unlinked=2, commodity_coverage=0.24, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.62, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **80.30** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 81.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=84.0, core=80.0, summary=82.0, missed=74.0, noise=78.0
- Summary: 전체 5건씩 채운 점은 좋지만, 기사 선택의 편집 밀도가 기대보다 낮다. 농협 2200억원 지원과 영주 여름사과 출하가 중복 배치됐고, 유통 섹션에는 기고성 홍보 기사와 교육 행사 기사가 핵심·상위 카드로 들어갔다. 정책에서는 신선란 수입·가격 인하 등 당일 정부 수급대책 핵심 후보를 놓쳤고, 병해충은 밤나무 드론방제 유사 테마가 반복됐다. 일간 브리핑으로는 사용 가능하나, 중복 제거와 핵심 후보 우선순위 보정이 필요하다.
- [major] duplicate_story: 농협, 2200억원 규모 ‘힘내라 우리 농업’ 프로젝트로 농가 부담 낮춘... - 6번 농협 2200억원 지원 기사와 같은 사안을 반복해 정책 슬롯을 낭비했다.
- [moderate] duplicate_story: 영주 여름 사과 본격 출하 …유통 경쟁력 강화 - 공급 4번 영주 사과 첫 출하와 사실상 같은 출하·공판장 개장 기사다.
- [moderate] promotional_filler: [기고] 고창 선운산 수박, 명품은 하루아침에 만들어지지 않는다 - 유통 운영 뉴스라기보다 지역 브랜드 홍보성 기고문이다.
- [moderate] weak_core: 감귤 경매사한테서 듣는 감귤 출하전략 - 도매시장 교육 행사로 유통 관련성은 있으나 핵심 카드로는 현장성·뉴스성이 약하다.
- [major] missed_candidate: 미국산 신선란 가격 인하…이마트서 30구 5890원→4980원 - 정부 수급안정대책반 회의와 신선란 2억개 수입·가격 인하를 담은 강한 정책 후보를 놓쳤다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
