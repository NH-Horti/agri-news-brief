## Daily Eval (2026-05-28)
- Overall: **82.00** (warn)
- Operational: **95.46**
- Quality gate: **82.00** (needs_iteration, editorial_below_target; editorial=82.0, operational=95.5)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.0, section_fit=100.0, core=100.0, commodity=96.6
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=145, policy:5/5 raw=90, dist:5/5 raw=30, pest:5/5 raw=51
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=5.09, false_positive=0.00, weak_core=0.00, editorial_penalty=3.2, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=78.0, section_fit=80.0, core=76.0, summary=89.0, missed=81.0, noise=74.0
- Summary: 구성 수는 모두 채웠지만, 편집 품질은 목표치에 못 미친다. 공급 섹션의 1번 코어가 홍보성 양파 소비 기사여서 핵심 뉴스 선택이 약했고, 배포·유통 섹션은 동일 MOU의 중복 성격 기사와 판촉·출하식성 지역 기사 비중이 높다. 병해충 섹션은 가장 중요한 화상병 확산·경계 격상 기사를 코어로 세우지 못한 점이 크다. 정책은 무난하지만 정부 수급회의 기사 중복이 있다. 요약문 자체는 대체로 쓸 만하나, 더 강한 전국 단위 이슈를 앞세웠어야 한다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 소비 홍보성 지역 기사로 공급 핵심 이슈성이 약함.
- [high] missed_opportunity: 과잉 양파 '수매'·부족 계란 '수입'…정부 "6~7월 물가 안정 총력" - 원시 후보에 더 강한 전국 단위 수급 기사 있었는데 미반영.
- [medium] promotional_filler: 괴산군 원원종 감자 생산 목표 초과 달성 - 지역 성과 홍보에 가깝고 당일 공급 현안성과 약함.
- [medium] duplicate_angle: 농축산물 물가, 맞춤형으로 대응 / 양파값 급락·계란값 고공행진…정부, 수급 안정·할인지원 총력 - 같은 정부 수급회의를 거의 반복해 정책면 효율 저하.
- [high] duplicate_story: 강원농협·농협공판장, 온라인 도매시장 활성화 앞장 / 강원 농산물 온라인 도매시장 경쟁력 키운다 - 동일 MOU의 사실상 중복 기사다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
