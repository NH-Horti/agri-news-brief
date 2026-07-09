## Daily Eval (2026-07-10)
- Overall: **72.05** (warn)
- Operational: **98.72**
- Reader quality: **98.72** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **72.05** (needs_major_iteration, editorial_blocking_issue; editorial=72.0, operational=98.7)
- Scores: completeness=100.0, diversity=100.0, summary=98.5, freshness=100.0, retrieval=87.5, section_fit=100.0, core=100.0, commodity=99.1
- Briefing cards: 20 / Commodity cards: 52
- Sections: supply:5/5 raw=200, policy:5/5 raw=145, dist:5/5 raw=91, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.85, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.85, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=6, commodity_active_today=13, commodity_active_today_unlinked=7, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **72.05** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 72.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=3, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=74.0, section_fit=75.0, core=66.0, summary=84.0, missed=62.0, noise=72.0
- Summary: 물량은 20건으로 채웠고 dist·pest 일부 핵심은 좋지만, supply 핵심에 농업과 무관한 노후주택 호우 안전 기사가 들어간 것이 큰 결함입니다. 양파 수급 안정 기사가 여러 섹션에 반복돼 지면 효율이 떨어졌고, policy 코어에 행사·금융 브리핑성 기사가 들어가 핵심성이 약합니다. 도매시장 제도 개선, 장마 뒤 채소값 상승 조짐, 농진청·도 단위 병해충 대응 등 더 나은 후보도 일부 누락됐습니다.
- [blocking] off_topic: [전국 톡톡] 장마철 장대비에 빨간불 켜진 '노후주택' - 노후주택·축대 안전 기사로 농산물 수급·생산·유통과 직접 관련이 없는데 supply 코어로 선정됐다.
- [major] weak_core: [농협] K-라이스페스타 접수 / NH콕뱅크 10주년 이벤트 / 양파 수급 안정 ... - 행사 접수와 금융 이벤트가 섞인 홍보성 브리핑으로 정책 코어로 보기 어렵다.
- [major] duplicate_theme: 양파 수급 안정·가격 반등 기사 다수 - supply·policy·dist에 양파 가격 회복/농협 수급대책이 반복돼 같은 논점을 과점한다.
- [major] missed_candidate: 공공성 강화·농협공판장 기능 확대 추진 - 도매시장 제도 개선·공판장 기능 강화는 dist의 핵심 시장운영 후보인데 지역 브랜드/수출 꼬리기사에 밀렸다.
- [moderate] missed_candidate: 장맛비 끝나면 채소값 오르나…산지 출하 감소에 가격 상승 '조짐' - 당일 호우와 산지 출하 감소가 채소 가격에 미칠 영향을 다룬 supply 적합 후보가 누락됐다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
