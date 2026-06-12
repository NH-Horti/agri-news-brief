## Daily Eval (2026-06-12)
- Overall: **86.00** (pass)
- Operational: **97.83**
- Reader quality: **97.65** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **86.00** (needs_iteration, editorial_below_target; editorial=86.0, operational=97.8)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.2, section_fit=97.2, core=92.0, commodity=100.0
- Briefing cards: 20 / Commodity cards: 14
- Sections: supply:5/5 raw=205, policy:5/5 raw=75, dist:5/5 raw=44, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=3.66, false_positive=0.00, hard_reader_issues=0, weak_core=0.17, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=7, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=87.0, core=88.0, summary=93.0, missed=79.0, noise=82.0
- Summary: 전반적으로 5개 섹션 충원과 핵심 이슈 포착은 잘 됐지만, 공급·정책·유통에서 약한 보충 기사와 섹션 경계가 흐린 카드가 섞이며 편집 완성도가 떨어졌다. 특히 공급 섹션에 기계화·행사성 기사 2건이 과하고, 정책 섹션도 전국 정책보다 지역 접수·농협 지원성 기사 비중이 높다. 유통은 일본 도매시장 혁신과 공판장 개장 등 좋은 축이 있으나 수박 출하 기사 2건은 판촉성에 치우쳤다. 병해충은 화상병 중심 축이 강하고 보조 기사도 대체로 적절하다.
- [high] weak_tail: 창녕서 마늘 전 과정 기계화 기술 공개…농촌 인력난 해법 제시 - 행사성 기술 공개 기사로 수급 직접성이 약함.
- [high] weak_tail: 경북 영천시, 마늘 수확 작업 기계화 및 농가 경영 효율화에 주력 - 지자체 장비 보급 기사로 전국 수급성 낮음.
- [medium] wrong_section_bias: 양파산업 위기 해법 찾는다 - 토론회·대책 논의 성격이 강해 정책 적합도가 더 높음.
- [medium] weak_tail: 횡성군, 2027년 유기질 비료 지원사업 접수 시작 - 지역 접수 안내성 기사로 정책 영향 범위가 좁음.
- [medium] weak_tail: 도시 농축협, 무이자자금 3771억원 지원 - 농협 내부 지원성 기사로 공공정책성 약함.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
