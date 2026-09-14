## Daily Eval (2026-09-15)
- Overall: **65.90** (fail)
- Operational: **93.38**
- Reader quality: **82.11** (capped; penalty=11.3, cap=90.0, reasons=pest_theme_duplicate, preferred_slot_underfill)
- Quality gate: **65.90** (needs_major_iteration, editorial_blocking_issue; editorial=65.9, operational=93.4)
- Scores: completeness=96.4, diversity=99.4, source=96.8, summary=96.8, freshness=100.0, retrieval=87.8, section_fit=100.0, core=100.0, commodity=100.0
- Briefing cards: 19 / Commodity cards: 37
- Sections: supply:5/5 raw=215, policy:5/5 raw=115, dist:5/5 raw=69, pest:4/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.74, low_tier=0.16, summary_presence=1.00, summary_numeric=0.79, fresh_72h=1.00, fit_avg=4.85, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=3.2, commodity_weak=0.00, commodity_items=9, commodity_active_today=14, commodity_active_today_unlinked=5, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.44, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **65.90** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 67.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=1, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min, no_section_underfill)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=68.0, section_fit=78.0, core=58.0, summary=72.0, missed=60.0, noise=58.0
- Summary: 형식과 신선도는 양호하지만 정책 핵심기사 중복, 유통 섹션의 행사성 기사 과다, 잘못 배치된 규제샌드박스 기사로 편집 밀도가 낮다. 공급·병해충은 상대적으로 안정적이다.
- [major] duplicate_story: 정부, 추석 할인 지원 예산 2.5배로…성수품도 초과 공급 - 앞 카드와 동일한 성수품 초과 공급·1490억원 할인 정책이며 둘 다 핵심이다.
- [blocking] off_topic: 짧은 추석 연휴, 여행 대신 고향 찾는다…부모님 용돈 평균 30만원 - 명절 소비 설문이 중심이고 농업정책 내용은 부수적이다.
- [moderate] weak_core: 농산물가격안정제 발동 기준, 평년 도매 가격 의 80% 수준으로 - 농가 경영안전망의 구체적 제도 변화로 중복된 추석 대책보다 핵심성이 높다.
- [moderate] weak_core: 175억 성공모델 남부권으로…달성 로컬푸드 직거래망 넓힌다 - 지역 직매장 개장 기사로 전국적 파급력과 운영 정보가 제한적이다.
- [moderate] wrong_section: [단독]농식품 규제샌드박스 83건 승인했는데…제도개선 완료 '단 1건' - 유통·물류보다 제도 운영 부진을 다룬 정책 기사다.

### Improvement Hints
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=11%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
