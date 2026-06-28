## Daily Eval (2026-06-26)
- Overall: **96.71** (pass)
- Operational: **96.71**
- Reader quality: **96.71** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **96.71** (target_met, all_targets_met; editorial=95.0, operational=96.7)
- Scores: completeness=100.0, diversity=90.0, summary=100.0, freshness=100.0, retrieval=83.8, section_fit=100.0, core=98.3, commodity=98.6
- Briefing cards: 20 / Commodity cards: 29
- Sections: supply:5/5 raw=160, policy:5/5 raw=110, dist:5/5 raw=59, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.60, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.07, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=10, commodity_active_today=14, commodity_active_today_unlinked=4, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Section count gate: 100.0 (target_met)
- Score calibration: 82.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=80.0, section_fit=84.0, core=85.0, summary=88.0, missed=74.0, noise=79.0
- Summary: 구성 수는 모두 채웠고 큰 섹션 오분류는 적지만, 공급·유통에서 중복/약한 꼬리 카드가 눈에 띄고 정책도 포럼·일손지원 같은 비핵심 비중이 높습니다. 특히 공급 섹션은 제주 월동채소 가격하락 기사 2건이 사실상 동일 사안이라 지면 효율이 떨어졌고, 유통 섹션은 같은 온라인도매시장 거봉 경매를 2건 넣어 중복이 큽니다. 원시 후보군에는 더 나은 운영형 유통 기사와 정책성 기사들이 보여서 90점대 주기는 어렵습니다.
- [high] duplicate: 제주 월동채소 생산 늘었지만 가격 '뚝' / 월동무 ·당근·양배추 생산량↑·소비부진으로 ' 가격 반토막' - 같은 제주 월동채소 작황·가격하락 사안을 중복 채택했다.
- [medium] weak_tail: 6월 채소류 농업관측 - 단순 관측 요약물로 당일성·차별성이 약하다.
- [medium] weak_tail: “ 양파 출하철 외상거래 주의”…표준계약서·증빙자료 챙겨야 - 지역성 강한 피해예방 공지에 가깝다.
- [medium] weak_core: 농협, ‘농산물 가격안정과 적정 생산체계 구축’ 방안 논의 - 포럼 개최 기사로 실행 정책 정보가 제한적이다.
- [medium] weak_tail: 농협, 2주간 전국 단위 범농협 농촌일손 집중지원 - 기관 활동성 홍보 기사 성격이 강하다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: policy, dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
