## Daily Eval (2026-07-02)
- Overall: **98.80** (pass)
- Operational: **98.80**
- Reader quality: **98.80** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **98.80** (target_met, all_targets_met; editorial=95.0, operational=98.8)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=87.5, section_fit=100.0, core=100.0, commodity=96.1
- Briefing cards: 20 / Commodity cards: 23
- Sections: supply:5/5 raw=172, policy:5/5 raw=190, dist:5/5 raw=81, pest:5/5 raw=30
- Metrics: title_unique=1.00, domain_diversity=0.85, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=4.24, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=7, commodity_active_today=12, commodity_active_today_unlinked=5, commodity_coverage=0.21, commodity_strict_link=0.86, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Score calibration: 84.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=83.0, section_fit=86.0, core=82.0, summary=82.0, missed=78.0, noise=79.0
- Summary: 전체 5개 섹션 슬롯은 모두 채웠고 주요 수급·정책·유통·병해충 이슈도 상당수 포착했다. 다만 정책과 병해충에서 같은 사안을 중복 채택했고, 공급 섹션에는 퀵커머스 같은 농업 현장성이 약한 소비 트렌드와 저임팩트 지역 실증 기사가 들어갔다. 원자료에 더 강한 정책 후보와 수출 검역·병해충 대응 후보가 보였는데 일부가 밀려 publish-quality에는 못 미친다.
- [major] duplicate_story: ‘금(金)계란’ 되지 않도록…정부, 계란 전품목 20% 할인 등 농축산물... - 3000억원 할인·계란 수입 대책은 이미 6번 카드와 같은 핵심 내용이다.
- [major] duplicate_story: 정읍시, 과수 전염병 ‘ 화상병 ’ 유입 막는다…현장 예찰 총력 - 17번 정읍 화상병 기사와 사실상 동일한 지역·사안 중복이다.
- [moderate] weak_section_fit: “퇴근 전 주문, 요리 전 배송”…장보기 문화 바꾼 퀵커머스 - 일반 유통·소비 트렌드 기사로 농산물 생산·수급 신호가 약하다.
- [moderate] low_impact_filler: 제주, 딸기 농가 휴경기 '대체작목' 육성한다 - 지역 실증 사업 성격이 강하고 당일 전국 수급 브리핑 임팩트가 낮다.
- [major] missed_better_candidate: 농산물 가격 안정 국내 생산 기반 확충서 찾아야 - 수입 확대 기조와 국내 생산기반 논쟁을 다루는 상위 정책 후보가 누락됐다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
