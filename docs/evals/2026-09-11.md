## Daily Eval (2026-09-11)
- Overall: **93.18** (pass)
- Operational: **96.63**
- Reader quality: **96.27** (clear; penalty=0.4, cap=100.0, reasons=clear)
- Quality gate: **93.18** (needs_major_iteration, editorial_major_issue; editorial=74.7, operational=96.6)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=89.4, section_fit=95.2, core=88.1, commodity=96.1
- Briefing cards: 20 / Commodity cards: 63
- Sections: supply:5/5 raw=320, policy:5/5 raw=160, dist:5/5 raw=64, pest:5/5 raw=30
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.20, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.20, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.2, commodity_weak=0.00, commodity_items=10, commodity_active_today=17, commodity_active_today_unlinked=7, commodity_coverage=0.30, commodity_strict_link=0.80, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **74.65** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 76.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=74.0, section_fit=86.0, core=63.0, summary=92.0, missed=67.0, noise=68.0
- Summary: 형식과 요약은 양호하지만, 동일 정책·농협 대책의 반복과 지역성·홍보성 꼬리기사가 많다. 특히 공급·병해충의 핵심기사 지정과 유통 후보 교체가 필요하다.
- [moderate] duplicate_story: '가격 급락' 뒤늦은 지원 손본다…충북도 농산물 선제 대응 / 농산물값 폭락 때 차액 지원…가격안정 조례 충북도의회 상임위 통과 - 같은 충북 가격안정 조례와 산정식을 중복 전달한다.
- [moderate] weak_core: 마늘·양파값 떨어지면 정부가 차액 보전…평년 도매가 80% 보장 - 전국 단위 신규 가격안정제인데 지역 조례 두 건보다 핵심성이 높다.
- [moderate] promotional_filler: 거창군, 포도 농가와 소통…현장의 어려움 함께 살펴 - 10여 명 규모의 현장 간담회로 구체적 조치나 시장 정보가 부족하다.
- [moderate] duplicate_theme: 농협경제지주, 농축산물 수급 안정 점검 / 농협, 추석 물가 안정에 877억원 투입 - 같은 농협 추석 수급·할인 대책을 두 카드가 반복한다.
- [moderate] missed_candidate: 가락시장, 9월 23일부터 추석 휴업…청과·수산부류별 경매 재개일 달라 - 출하 농가에 직접 필요한 시장 운영 일정인데 지역 쇼핑몰 기사에 밀렸다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
