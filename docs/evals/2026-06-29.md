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
- Score calibration: 86.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=85.0, section_fit=88.0, core=86.0, summary=82.0, missed=80.0, noise=84.0
- Summary: 분량은 4개 섹션 모두 5건으로 충족했고, 물가·양파·온라인도매·과수화상병 등 핵심 축은 대체로 잡았다. 다만 공급·유통에 지역 행사성 꼬리기사가 섞였고, 병해충은 고추 탄저병 지역 안내가 과다 반복되면서 토마토뿔나방 검역 완화, 단감 노린재 방제 같은 더 구체적인 후보를 놓쳤다. 정책도 물가대책 중복감이 있어 노동력·할당관세 등 다른 농정 이슈로 넓힐 여지가 있었다. 요약에는 원문 크롤링 잡음이 남아 독자용 완성도를 낮춘다.
- [medium] weak_filler: 보령 사현 포도 , 26일 올해 첫 수확 본격 출하 - 지역 첫 수확·출하 행사성 기사로 전국 수급 중요도가 낮다.
- [medium] missed_opportunity: 기후위기 직격탄…고랭지 농사 ‘먹구름’ - 여름배추 재배의향 감소와 수급 불안은 포도 첫 출하보다 훨씬 중요한 공급 리스크다.
- [high] weak_filler: 구천동농협 여수농협 임직원 초청 영농 현장체험 - 임직원 견학·체험 중심의 홍보성 지역 기사로 유통 운영 정보가 약하다.
- [low] soft_filler: 여주 대신농협, 가락공판장 찾아 ‘ 농산물 제값받기’ 협력 논의 - 공판장 방문·간담회 성격이 강해 실제 유통 변화나 물량 정보가 제한적이다.
- [high] duplicate_theme: 서산시/해남군/경북 고추 탄저병·병해충 주의 기사들 - 고추 장마철 병해충 안내가 3건 반복돼 병해충 브리핑의 정보 폭이 좁아졌다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
