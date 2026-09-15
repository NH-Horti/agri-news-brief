## Daily Eval (2026-09-16)
- Overall: **68.50** (fail)
- Operational: **93.99**
- Reader quality: **85.04** (capped; penalty=8.9, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **68.50** (needs_major_iteration, editorial_blocking_issue; editorial=68.5, operational=94.0)
- Scores: completeness=100.0, diversity=95.8, source=100.0, summary=100.0, freshness=100.0, retrieval=87.9, section_fit=91.7, core=92.4, commodity=100.0
- Briefing cards: 20 / Commodity cards: 34
- Sections: supply:5/5 raw=267, policy:5/5 raw=130, dist:5/5 raw=91, pest:5/5 raw=27
- Metrics: title_unique=1.00, domain_diversity=0.65, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.32, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=2.8, commodity_weak=0.00, commodity_items=7, commodity_active_today=17, commodity_active_today_unlinked=10, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **68.50** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 68.50; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=2, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=66.0, section_fit=72.0, core=66.0, summary=90.0, missed=58.0, noise=58.0
- Summary: 20건 구성과 요약은 충실하지만, 동일 인천 수급점검을 세 번 싣고 경매 카드결제도 중복했다. 비농업 지자체 대책과 행사성 기사까지 포함돼 원자료 규모에 비해 선별력이 부족하다.
- [major] duplicate_story: 인천농협, 추석 명절 농산물 수급 상황 점검 - 공급 1번 및 유통 13번과 동일한 남촌시장 현장점검 기사다.
- [major] duplicate_story: 농산물 경매대금도 카드로…NHN KCP, B2B 결제 확대 - 14번과 동일한 카드결제 인프라 발표를 반복한다.
- [blocking] off_topic: 대구 동구, 추석맞이 종합 대책 추진 - 농업 정책이나 농산물 수급과 직접 관련 없는 일반 지자체 연휴 대책이다.
- [moderate] wrong_section: 느타리·봄동·제주당근까지…가락시장 파렛트 의무출하 가속 - 출하 물류와 하역 효율 개선이 핵심인 유통 기사다.
- [moderate] weak_core: 농협 인천본부, 추석 앞두고 사과 ·배·무·배추 수급 점검 - 지역 기관의 현장 방문으로 실질 수급 데이터가 부족해 핵심 기사로 약하다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
