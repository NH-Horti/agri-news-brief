## Daily Eval (2026-06-29)
- Overall: **95.28** (pass)
- Operational: **95.28**
- Reader quality: **95.28** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **95.28** (target_met, all_targets_met; editorial=95.0, operational=95.3)
- Scores: completeness=100.0, diversity=90.0, summary=98.5, freshness=91.4, retrieval=82.0, section_fit=100.0, core=100.0, commodity=99.1
- Briefing cards: 20 / Commodity cards: 52
- Sections: supply:5/5 raw=221, policy:5/5 raw=105, dist:5/5 raw=64, pest:5/5 raw=23
- Metrics: title_unique=1.00, domain_diversity=0.60, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.75, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=10, commodity_active_today=17, commodity_active_today_unlinked=7, commodity_coverage=0.30, commodity_strict_link=0.90, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Score calibration: 85.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=84.0, section_fit=86.0, core=82.0, summary=77.0, missed=78.0, noise=80.0
- Summary: 분량은 전 섹션 5건으로 맞췄고, 오이·양파 수급, 정부 물가대책, 온라인 도매시장, 과수화상병 등 핵심 축은 대체로 잡았다. 다만 원자료에 더 강한 후보가 보이는데도 지역 첫 출하·현장체험·일반 방제 당부 같은 약한 꼬리 기사가 들어갔고, 정책은 1조 물가대책 계열 중복, 병해충은 고추 탄저병 경고가 과다 반복됐다. 일부 요약은 크롤링 잔재가 많아 독자용 브리핑 품질을 떨어뜨린다.
- [medium] weak_tail: 보령 사현 포도 , 26일 올해 첫 수확 본격 출하 - 지역 첫 수확·출하 알림 성격이 강해 수급 브리핑 핵심도가 낮다.
- [medium] missed_better_candidate: 기후위기 직격탄…고랭지 농사 ‘먹구름’ - 여름배추 재배의향 감소와 수급·가격 불안 신호가 더 전국적이고 중요하다.
- [medium] duplication: 국정 2년차, 물가와의 전쟁…'가격 개입' 현실화 - 계란·1조 물가대책 카드와 정책축이 상당히 겹친다.
- [medium] missed_better_candidate: 먹거리 할당관세 확대…내 식탁엔 무엇이 달라질까? [나유정] - 수입·관세 정책의 품목별 영향을 설명해 중복 물가대책 기사보다 활용도가 높다.
- [high] promotional_filler: 구천동농협 여수농협 임직원 초청 영농 현장체험 - 임직원 견학·체험 행사 중심으로 유통 운영 뉴스성이 약하다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
