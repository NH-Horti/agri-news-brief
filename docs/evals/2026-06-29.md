## Daily Eval (2026-06-29)
- Overall: **96.38** (pass)
- Operational: **96.38**
- Reader quality: **96.38** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **96.38** (target_met, all_targets_met; editorial=95.0, operational=96.4)
- Scores: completeness=100.0, diversity=95.0, summary=100.0, freshness=92.9, retrieval=82.0, section_fit=98.6, core=98.3, commodity=100.0
- Briefing cards: 20 / Commodity cards: 49
- Sections: supply:5/5 raw=221, policy:5/5 raw=105, dist:5/5 raw=64, pest:5/5 raw=23
- Metrics: title_unique=1.00, domain_diversity=0.65, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.64, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=10, commodity_active_today=17, commodity_active_today_unlinked=7, commodity_coverage=0.30, commodity_strict_link=0.90, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.40, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Section count gate: 100.0 (target_met)
- Score calibration: 82.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=80.0, section_fit=84.0, core=83.0, summary=88.0, missed=76.0, noise=79.0
- Summary: 구성 수는 목표를 채웠고 대체로 농업 독자 관심사에 맞췄지만, 중복·유사 정책 기사와 양파 반복, dist·pest의 약한 꼬리 카드, 그리고 더 강한 후보를 두고 선택한 흔적이 보여 95점대 평가는 어렵다. 공급은 이슈성은 있으나 양파 중복이 과하고 오이 급등과 오이·애호박 급락 같은 상반된 시장 신호를 더 정리했어야 한다. 정책은 정부 1조 물가대책을 3건이나 실어 중복도가 높다. dist는 운영형 기사 2건은 좋지만 로컬푸드 성공담·해외 연수단 방문은 편집 강도가 약하다. pest는 화상병 확산 기사보다 칼럼성 취재수첩을 코어로 둔 점이 아쉽고, 지역 방제 공지성 기사 비중이 높다.
- [high] duplication: 양파 관련 2건 동시 선정 - 같은 경북도 양파 가격하락 대응을 사실상 중복 게재했다.
- [high] duplication: 정부 물가대책 3건 반복 - 1조 투입·할인지원 중심으로 내용이 거의 겹친다.
- [high] missed_opportunity: 오이·애호박 값 반토막 기사 미선정 - 구체적 산지 고통과 가격 하락을 보여주는 강한 수급 기사였다.
- [medium] weak_core: [취재수첩] 과수화상병이 ‘개꿀’이라니 - 현장성은 있으나 코어로는 데이터형 확산 기사보다 약하다.
- [medium] wrong_priority: 파라과이 연수단 ‘한반도 농협 스마트 APC’ 방문 - 벤치마킹 방문 소식은 유통 운영 이슈성보다 홍보성이 강하다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
