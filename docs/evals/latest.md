## Daily Eval (2026-09-15)
- Overall: **85.98** (warn)
- Operational: **95.06**
- Reader quality: **90.25** (clear; penalty=4.8, cap=100.0, reasons=clear)
- Quality gate: **85.98** (needs_major_iteration, editorial_major_issue; editorial=69.9, operational=95.1)
- Scores: completeness=100.0, diversity=92.9, source=100.0, summary=100.0, freshness=100.0, retrieval=87.8, section_fit=100.0, core=100.0, commodity=100.0
- Briefing cards: 20 / Commodity cards: 35
- Sections: supply:5/5 raw=215, policy:5/5 raw=115, dist:5/5 raw=69, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.15, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.57, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.7, commodity_weak=0.00, commodity_items=9, commodity_active_today=14, commodity_active_today_unlinked=5, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.44, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **69.90** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 69.90; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=73.0, section_fit=78.0, core=58.0, summary=89.0, missed=62.0, noise=57.0
- Summary: 형식과 요약은 양호하지만 정책 중복 3건, 유통의 행사성 핵심기사, 병해충 교육·상식성 채움이 편집 품질을 크게 낮춘다. 더 강한 운영·방제 후보가 원문 풀에 있었다.
- [major] duplicate_story: 정부, 추석 할인 지원 예산 2.5배로…성수품도 초과 공급 - 6·7·9번이 모두 같은 성수품 초과 공급·할인 확대 발표다.
- [moderate] weak_core: 정부, 추석 할인 지원 예산 2.5배로…성수품도 초과 공급 - 동일 발표가 이미 핵심으로 선정돼 중복 핵심이다. 이 카드는 core에서 강등해야 한다.
- [moderate] promotional_filler: 화성 송산농협, 아태 15개국에 포도 생산·수출 현장 소개 - 수출 실적이나 신규 계약 없이 시설 견학 중심인 홍보성 기사다.
- [moderate] weak_core: 신북 농협 , 배 수출 확대로 농가소득 증대 기여 - 선적 기념식과 목표 제시가 중심으로 실적 근거가 약하다. core에서 강등해야 한다.
- [moderate] wrong_section: [단독]농식품 규제샌드박스 83건 승인했는데…제도개선 완료 '단 1건' - 유통·물류·판로보다 제도 성과를 다룬 정책 기사다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
