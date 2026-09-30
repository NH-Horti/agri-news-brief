## Daily Eval (2026-10-01)
- Overall: **58.65** (fail)
- Operational: **88.60**
- Reader quality: **83.88** (capped; penalty=4.7, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **58.65** (needs_major_iteration, editorial_blocking_issue; editorial=58.6, operational=88.6)
- Scores: completeness=89.2, diversity=93.2, source=65.9, summary=100.0, freshness=100.0, retrieval=70.8, section_fit=77.8, core=100.0, commodity=87.0
- Briefing cards: 17 / Commodity cards: 21
- Sections: supply:5/5 raw=199, policy:5/5 raw=68, dist:5/5 raw=48, pest:2/5 raw=7
- Metrics: title_unique=1.00, domain_diversity=0.76, low_tier=0.24, summary_presence=1.00, summary_numeric=0.82, fresh_72h=1.00, fit_avg=2.65, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=6, commodity_active_today=12, commodity_active_today_unlinked=6, commodity_coverage=0.18, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=1.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **58.65** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 58.50; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=5, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min, section_count_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 87.5 (underfilled)
- Components: article_selection=55.0, section_fit=61.0, core=64.0, summary=82.0, missed=43.0, noise=42.0
- Summary: 요약은 명료하지만 중복 기사, 비농업 정책 기사, 판촉성 꼬리기사와 강한 후보 누락이 많다. 특히 공급·유통에서 같은 사안을 두 번씩 담고, pest는 활용 가능한 피해 기사 대신 2건에 그쳐 편집 완성도가 낮다.
- [major] duplicate_story: 도쿄 35일 연속 비 ‘1886년 이래 최장’…채솟값 뛰고 두통 호소도 - 3번과 동일한 도쿄 장기 강우·채소 가격 전망 기사다.
- [major] duplicate_story: "온라인 도매시장서 25% '이상거래'…특수관계·순환거래 기승" - 11번과 동일 통계와 조사에 기반한 같은 사건이다.
- [major] duplicate_story: 기계-영상-인공지능 적용 깐마늘 선별 “자동화 넘어 지능화” - 13번과 같은 농진청 깐마늘 선별 시스템 발표다.
- [blocking] off_topic: 김선기 KTL 원장 취임…첨단 산업 시험인증·기업 수출 지원 강화 - 농업·원예 정책과 직접 연결되지 않은 일반 산업기관장 취임 기사다.
- [major] missed_candidate: 위상 높인 농산물 수급조절위 8기 닻 올려… "과수까지 품고 수급관리" - 법정위원회 전환과 과수 수급관리 확대를 다룬 최상위 정책 후보가 누락됐다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-3). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 12%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
