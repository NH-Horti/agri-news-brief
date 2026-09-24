## Daily Eval (2026-09-16)
- Overall: **83.17** (warn)
- Operational: **93.37**
- Reader quality: **84.42** (capped; penalty=8.9, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **83.17** (needs_major_iteration, editorial_acceptance_gate_failed; editorial=77.0, operational=93.4)
- Scores: completeness=100.0, diversity=92.4, source=80.0, summary=100.0, freshness=100.0, retrieval=87.9, section_fit=91.7, core=92.1, commodity=100.0
- Briefing cards: 20 / Commodity cards: 34
- Sections: supply:5/5 raw=267, policy:5/5 raw=130, dist:5/5 raw=91, pest:5/5 raw=27
- Metrics: title_unique=1.00, domain_diversity=0.65, low_tier=0.20, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=3.84, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=2.8, commodity_weak=0.00, commodity_items=7, commodity_active_today=17, commodity_active_today_unlinked=10, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **77.00** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 78.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=75.0, section_fit=75.0, core=74.0, summary=90.0, missed=70.0, noise=82.0
- Summary: 20장 구성과 요약은 충실하지만, 공급·정책·유통에서 섹션 오배치와 약한 지역성 카드가 강한 후보를 밀어냈다. 특히 파렛트 물류 중복과 워크숍의 핵심 지정이 편집 완성도를 낮춘다.
- [moderate] wrong_section: 마늘·양파 생산자단체 "새 농안법, 실질적 가격 안전망 돼야" - 가격안정제와 농안법 개선 요구가 중심인 정책 기사다.
- [moderate] duplicate_theme: 봄동·당근 파렛트 출하 의무화 - 유통의 ‘가락시장 파렛트 물류 전환’과 사실상 같은 정책·품목을 반복한다.
- [moderate] promotional_filler: 청주 내수농협, 계약 재배 농가에 영농자재 지원 - 76명 대상 지역 농협 지원 사례로 전국 정책 가치가 낮다.
- [moderate] missed_candidate: 모처럼 농축산물 가격 안정...추석 차례상 비용도 '뚝' - 품목별 가격 변동 수치가 풍부해 지역 지원·회의 기사보다 정책 독자에게 유용하다.
- [moderate] weak_core: 경남 원예조공법인, 온라인도매시장 대응·연합판매 경쟁력 강화 - 워크숍 개최 중심이라 핵심 유통 변화로 보기 어렵다. core에서 demote해야 한다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
