## Daily Eval (2026-09-16)
- Overall: **89.94** (warn)
- Operational: **94.22**
- Reader quality: **90.44** (clear; penalty=3.8, cap=100.0, reasons=clear)
- Quality gate: **89.94** (needs_iteration, editorial_acceptance_gate_failed; editorial=81.3, operational=94.2)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=87.9, section_fit=90.3, core=88.2, commodity=100.0
- Briefing cards: 20 / Commodity cards: 34
- Sections: supply:5/5 raw=267, policy:5/5 raw=130, dist:5/5 raw=91, pest:5/5 raw=27
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.20, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=4.09, false_positive=0.00, hard_reader_issues=0, weak_core=0.11, editorial_penalty=2.1, commodity_weak=0.00, commodity_items=7, commodity_active_today=17, commodity_active_today_unlinked=10, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **81.30** (daily target 82, tier=needs_iteration, needs_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 81.30; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=81.0, section_fit=87.0, core=76.0, summary=90.0, missed=78.0, noise=76.0
- Summary: 정량·운영 정보와 섹션 수는 충실하지만, 일부 현장행사성 기사와 일반 회의가 포함됐고 dist·supply의 핵심기사 지정이 약하다. 정책 섹션도 추석 물가 주제가 다소 과밀하다.
- [moderate] weak_core: 추석 출하 과일 안정 생산 기술지원 박차 - 단일 산지 방문·기술지원 기사로 전국 수급 핵심기사로는 영향력이 제한적이다.
- [moderate] promotional_filler: 홍성군농업기술센터, 마늘 파종 기계화로 농가 인력난 돌파구 마련 - 지역 농기계 연시회 중심이며 생산비 절감 효과도 구체적으로 제시되지 않았다.
- [moderate] weak_core: 경남 원예조공법인, 온라인도매시장 대응·연합판매 경쟁력 강화 - 워크숍 개최와 협의가 중심이라 실제 유통 운영 변화가 부족하다.
- [moderate] weak_core: 가락시장 '파렛트 물류' 전환 가속 - 품목별 의무화 일정이 확정된 직접적인 물류 운영 변화로 핵심성이 높다.
- [moderate] duplicate_theme: 모처럼 농축산물 가격 안정...추석 차례상 비용도 '뚝' - 성수품 공급 확대·축산물 가격 대응 기사와 함께 추석 물가 주제가 세 자리를 차지한다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
