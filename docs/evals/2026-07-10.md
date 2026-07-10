## Daily Eval (2026-07-10)
- Overall: **75.50** (warn)
- Operational: **96.30**
- Reader quality: **94.42** (capped; penalty=1.9, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **75.50** (needs_major_iteration, editorial_blocking_issue; editorial=75.5, operational=96.3)
- Scores: completeness=96.4, diversity=99.4, source=96.8, summary=98.4, freshness=100.0, retrieval=86.9, section_fit=100.0, core=100.0, commodity=94.9
- Briefing cards: 19 / Commodity cards: 54
- Sections: supply:4/5 raw=188, policy:5/5 raw=141, dist:5/5 raw=84, pest:5/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.84, low_tier=0.16, summary_presence=1.00, summary_numeric=0.68, fresh_72h=1.00, fit_avg=3.48, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.2, commodity_weak=0.00, commodity_items=5, commodity_active_today=15, commodity_active_today_unlinked=10, commodity_coverage=0.15, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.60, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **75.50** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 77.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=3, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=78.0, section_fit=74.0, core=73.0, summary=81.0, missed=71.0, noise=75.0
- Summary: 유통(dist)과 병해충(pest)은 대체로 현장성이 있고 핵심 기사도 무난하지만, 정책(policy)에 농업 관련성이 약한 몽골 관세 기사가 들어가고 공급(supply)·정책 코어가 섹션 성격과 어긋난 점이 크다. 공급 섹션은 원자료가 충분한데 4건으로 끝났고, 더 강한 가격안정·채소 수급 후보를 놓친 대신 지역 신청 공고성 기사와 기술/R&D 성격 기사를 넣었다. 전체적으로 사용 가능성은 있으나 데일리 편집 승인에는 교체와 재배치가 필요하다.
- [blocking] off_topic: 몽골산 ‘캐시미어’·희토류 수입 관세 없앴다… 韓 화장품·의약품 수... - 농업·원예 독자에게 직접성이 낮은 통상 일반 기사이며 요약도 농산물 관련 내용이 없다고 인정한다.
- [major] wrong_section: 장맛비 끝나면 채소값 오르나…산지 출하 감소에 가격 상승 '조짐' - 정책보다 기상 이후 산지 출하·채소 가격 전망 기사로 supply 성격이 강한데 policy 코어로 배치됐다.
- [major] weak_core: 농림위성으로 첨단농업 실현 기대 - 농림위성 활용 전망은 R&D·기술 정책에 가까워 공급/수급 코어로는 약하다.
- [moderate] underfill: supply section - 원자료가 충분한데 공급 섹션이 목표 5건이 아닌 4건으로 마감됐다.
- [moderate] promotional_filler: 청양군농업기술센터, 가을 배추 우량묘 110만 본 공급 - 지역 신청 안내 성격이 강해 전국 농업 브리핑의 공급 카드로는 꼬리 기사 품질이 낮다.

### Improvement Hints
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=11%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
