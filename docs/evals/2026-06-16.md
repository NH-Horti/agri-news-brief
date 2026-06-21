## Daily Eval (2026-06-16)
- Overall: **93.21** (pass)
- Operational: **95.31**
- Reader quality: **93.81** (capped; penalty=1.5, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **93.21** (needs_iteration, editorial_below_target_bounded_penalty; editorial=89.0, operational=95.3)
- Scores: completeness=92.8, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=100.0, commodity=100.0
- Briefing cards: 18 / Commodity cards: 38
- Sections: supply:5/5 raw=164, policy:4/5 raw=94, dist:4/5 raw=43, pest:5/5 raw=58
- Metrics: title_unique=1.00, domain_diversity=0.78, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.15, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=9, commodity_active_today=12, commodity_active_today_unlinked=3, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.44, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **89.00** (target 95, needs_iteration)
- Section count gate: 96.0 (soft_fallback)
- Components: article_selection=87.0, section_fit=82.0, core=84.0, summary=92.0, missed=86.0, noise=80.0
- Summary: 전반적으로 당일 농정·수급 이슈를 많이 담았지만, 정책·유통 섹션의 편성 완성도가 떨어진다. 특히 정책에 비농업 무관 기사가 들어갔고, 유통은 청송 사과 공판장 기사 3건이 사실상 중복 편성돼 다양성과 운영성 모두 약화됐다. 공급은 마늘·양파 중심의 현안 포착은 괜찮지만 양파 소비촉진 캠페인 같은 약한 꼬리 기사가 강한 대체 후보를 밀어냈다. 병해충은 화상병 중심축은 맞지만 주간농사메모는 너무 일반적이다. 원자료 풀이 충분한 날이라 95점대는 어렵다.
- [high] wrong_section_or_irrelevant: 복지부, 탈모 건보 적용 공식화…'청년층'부터 확대 추진 - 농업·농정과 무관한 비섹션 기사다.
- [high] duplication: 청송 사과 공판장 관련 3건 중복 편성 - 같은 사건을 유통 섹션 4건 중 3건으로 과다 반복했다.
- [medium] weak_tail: NH농협생명·생보협회, 양파 소비촉진 캠페인 실시 - 프로모션성 소비촉진으로 정보 밀도가 낮다.
- [high] weak_core: 본격 수확철 쏟아지는 양파에 눈물겨운 양파값 - 정책 코어치고 지역 가격기사 성격이 강하다.
- [medium] missed_opportunity: 무기질비료 가격 보조 추경 115억 신속 집행 - 실제 정책성은 높지만 비핵심 꼬리로만 처리됐다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1), dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
