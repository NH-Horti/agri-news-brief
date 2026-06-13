## Daily Eval (2026-06-12)
- Overall: **86.00** (pass)
- Operational: **97.12**
- Reader quality: **96.94** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **86.00** (needs_iteration, editorial_below_target; editorial=86.0, operational=97.1)
- Scores: completeness=93.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.2, section_fit=100.0, core=100.0, commodity=96.1
- Briefing cards: 20 / Commodity cards: 14
- Sections: supply:5/5 raw=204, policy:5/5 raw=74, dist:5/5 raw=44, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.85, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=3.51, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=7, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=88.0, core=87.0, summary=93.0, missed=80.0, noise=82.0
- Summary: 전반적으로 20건을 모두 채우고 핵심 이슈인 양파 수익성 악화, 여름배추 수급, 과수화상병 확산, 도매시장 물류 혁신 등을 잡아 기본 틀은 괜찮다. 다만 정책 섹션의 코어 부재와 약한 꼬리 기사, 유통 섹션의 판촉성·지역 개장성 기사 혼입, 공급 섹션의 매실 중복 계열 편중이 점수를 깎는다. raw pool을 보면 policy에서는 ‘농민의길…농특세’가 더 강한 선두감이었고, dist에서는 더 강한 출하/공선 기사와 디지털 유통 전환 기사 활용 여지가 있었다. 형식은 충족했지만 기사 선택의 날카로움은 목표 95점 수준에 못 미친다.
- [high] missed_better_candidate: 양파산업 위기 해법 찾는다 - 더 강한 정책 1순위는 농민의길 농특세 기사였다.
- [high] weak_core: 정책 섹션 전반 - raw 후보가 충분한데 코어 지정이 하나도 없다.
- [medium] filler: 횡성군, 2027년 유기질 비료 지원사업 접수 시작 - 전국성 파급이 약한 지자체 접수 안내성 기사다.
- [medium] weak_selection: [국가책임농정 1년] 역대 최고 농가소득 달성 속 예산·법제화 등 지속... - 평가·홍보 성격이 강하고 당일 현안성은 약하다.
- [medium] wrong_emphasis: 제주 블루베리 판매 량 73% 증가 '껑충' - 판촉·실적 홍보성 강해 dist 우선순위가 낮다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
