## Daily Eval (2026-05-28)
- Overall: **98.13** (pass)
- Operational: **98.13**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.0, section_fit=100.0, core=100.0, commodity=96.6
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=145, policy:5/5 raw=92, dist:5/5 raw=30, pest:5/5 raw=49
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=5.00, false_positive=0.00, weak_core=0.00, editorial_penalty=0.5, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **80.00** (target 95, needs_major_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=77.0, section_fit=79.0, core=72.0, summary=88.0, missed=76.0, noise=74.0
- Summary: 카드 수는 목표를 채웠지만 기사 고르기가 발행용 수준에는 못 미칩니다. 공급은 소비촉진 홍보물과 지역 씨감자 성과물이 핵심·꼬리로 섞여 가장 약했고, 정책은 같은 정부 수급회의 계열이 중복돼 효율이 떨어졌습니다. 유통은 온라인도매시장 기사는 적절했지만 지역 출하식·판촉전 비중이 높고 사실상 중복 기사도 포함됐습니다. 병해충은 과수화상병이 맞는 축이지만 가장 중요한 신규 발생·경계 격상 기사를 코어로 세우지 못한 점이 큽니다. 요약문 자체는 대체로 무난하나, 원 기사 선택의 약점을 가리진 못합니다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 소비촉진 홍보성 지역 기사인데 공급 섹션 코어로는 약함.
- [high] filler: 괴산군 원원종 감자 생산 목표 초과 달성 - 지역 성과 보도 성격이 강해 당일 전국 수급 판단에 기여가 낮음.
- [medium] duplication: 농축산물 물가, 맞춤형으로 대응 / 양파값 급락·계란값 고공행진…정부, 수급 안정·할인지원 총력 - 동일 정부 수급회의 재가공 기사로 중복성이 큼.
- [high] missed_core: 충남 공주서 과수화상병 신규 확인…농진청, 위기 단계 '주의'→'경계' ... - 당일 가장 강한 화상병 뉴스인데 비코어 처리됨.
- [medium] weak_core: 아산시, 과수화상병 차단 총력… 생육기 방제약제 전 농가 무상 지원 - 지원 안내는 유용하지만 발생·확산 기사보다 뉴스 강도가 약함.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
