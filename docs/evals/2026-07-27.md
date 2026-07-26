## Daily Eval (2026-07-27)
- Overall: **69.25** (fail)
- Operational: **94.38**
- Reader quality: **93.63** (capped; penalty=0.8, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **69.25** (needs_major_iteration, editorial_blocking_issue; editorial=69.2, operational=94.4)
- Scores: completeness=96.4, diversity=95.2, source=75.8, summary=96.8, freshness=90.8, retrieval=91.9, section_fit=100.0, core=93.2, commodity=100.0
- Briefing cards: 19 / Commodity cards: 21
- Sections: supply:5/5 raw=247, policy:5/5 raw=151, dist:4/5 raw=49, pest:5/5 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.84, low_tier=0.21, summary_presence=1.00, summary_numeric=0.53, fresh_72h=1.00, fit_avg=3.99, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=7, commodity_active_today=10, commodity_active_today_unlinked=3, commodity_coverage=0.21, commodity_strict_link=0.86, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **69.25** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 72.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=5, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min, operational_score_min, no_section_underfill)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=72.0, section_fit=75.0, core=66.0, summary=72.0, missed=60.0, noise=70.0
- Summary: 핵심 농정·유통 기사 일부는 잘 잡았지만, 공급 섹션에 반려견 간식 홍보성 기사가 core로 들어간 것이 치명적입니다. 정책에는 고랭지 채소 가격폭락 현장 기사가 잘못 배치됐고, 유통은 원자료가 충분한데도 4건으로 underfill되며 온라인도매시장 성과 논란 같은 더 강한 후보를 놓쳤습니다. 요약문 반복·절단도 여러 건 보여 일일 브리핑 품질은 통과선 아래입니다.
- [blocking] off_topic: 동원 F&B 아르르, 반려견용 '밥·꾸 간식' 착한 가격 에 만난다[펫과함께... - 반려견 간식 제품 소개로 농산물 수급·가격·생산 이슈와 거리가 멀고 홍보성이다. core 지정은 부적절하다.
- [major] missed_candidate: 결주에 흉작까지…강원 감자 농가의 눈물 - 씨감자 품질 논란, 공급량 부족, 흉작을 다루는 강한 생산·수급 기사인데 약한 기고·홍보성 카드에 밀렸다.
- [major] wrong_section: ［이슈 현장 ］홍천 내면 고랭지 채소 폐기 속출 “저장고 확충 시급” - 가격 폭락·산지 폐기 현장 기사로 공급 또는 유통 섹션이 맞으며, 공급의 무 가격 폭락 카드와 주제도 겹친다.
- [moderate] weak_core: [정부 주요 일정] 경제·사회부처 주간 일정 (7월 27일 ~ 7월 31일) - 주간 일정 나열은 독자 효용이 낮은 캘린더성 카드이며 정책 핵심 기사로 보기 어렵다.
- [major] missed_candidate: CPTPP 가입론 다시 수면 위로…농업계 "메가톤급 시장개방 우려" - 농업계 시장개방 리스크와 정부 검토 흐름을 다룬 전국 단위 정책 이슈인데 선택되지 않았다.

### Improvement Hints
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
