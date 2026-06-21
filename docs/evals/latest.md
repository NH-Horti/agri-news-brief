## Daily Eval (2026-06-22)
- Overall: **93.46** (pass)
- Operational: **94.56**
- Reader quality: **94.56** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **93.46** (needs_iteration, editorial_below_target_bounded_penalty; editorial=84.0, operational=94.6)
- Scores: completeness=100.0, diversity=90.0, summary=100.0, freshness=90.0, retrieval=88.8, section_fit=100.0, core=87.8, commodity=90.2
- Briefing cards: 20 / Commodity cards: 42
- Sections: supply:5/5 raw=247, policy:5/5 raw=243, dist:5/5 raw=74, pest:5/5 raw=83
- Metrics: title_unique=1.00, domain_diversity=0.60, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=5.05, false_positive=0.00, hard_reader_issues=0, weak_core=0.17, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=13, commodity_active_today=17, commodity_active_today_unlinked=4, commodity_coverage=0.39, commodity_strict_link=0.77, commodity_false_link=0.00, commodity_dominant_section=0.54, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=78.0, core=74.0, summary=91.0, missed=79.0, noise=77.0
- Summary: 구색은 5×4로 맞췄고 요약도 대체로 유용하지만, 편집 선택은 90점대에 못 미친다. 공급은 시황·마늘·양파 이슈를 담았으나 토론회/피처성 기사 비중이 높고 더 나은 정책·수급 후보를 놓쳤다. 정책은 정부 비축 확대를 잘 잡았지만 대통령 발언 2건이 사실상 중복이고, 할당관세 연장·수입란 공급 같은 더 직접적인 정책 카드가 빠졌다. 유통은 핵심으로 칼럼을 올린 것이 가장 큰 감점이며, 가락시장 배추 경매 시간 조정 같은 운영 기사로 대체했어야 했다. 병해충은 과수화상병 중심은 맞지만 용인 주간종합·일반 기술지도·진단서비스는 약하고, 보은·공주 등 더 구체적 확산/방제 기사 조합이 가능했다.
- [high] wrong_core: [천자칼럼] 히트플레이션 - 유통 운영·물류 기사보다 시사 칼럼 성격이 강함.
- [high] missed_opportunity: 국산 과일 한창때 ‘할당관세’ 재 뿌리나 - 직접적 정책 영향이 큰 상위 후보를 누락.
- [high] duplicate: 李대통령 물가 대응 2건 - 같은 회의·같은 메시지의 중복 선택.
- [medium] weak_tail: 송옥주 의원, 농산물 가격안정제 정책토론회 개최 - 행사 소개 위주로 공급면 핵심성이 약함.
- [medium] weak_tail: "지금 아니면 못 먹어"… 가격 20% 뛰어도 잘 나가는 채소 - 리테일 피처 성격이 강하고 공급 전반성 약함.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
