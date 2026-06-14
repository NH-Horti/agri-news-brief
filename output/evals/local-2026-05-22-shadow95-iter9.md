## Daily Eval (2026-05-22)
- Overall: **97.92** (pass)
- Operational: **97.92**
- Scores: completeness=100.0, diversity=96.7, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=100.0, commodity=91.3
- Briefing cards: 12 / Commodity cards: 42
- Sections: supply:3/3 raw=156, policy:3/3 raw=172, dist:3/3 raw=53, pest:3/3 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.67, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=5.15, false_positive=0.00, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=86.0, core=83.0, summary=74.0, missed=79.0, noise=88.0
- Summary: 전반적으로 섹션 수는 맞췄고 양파·가격안정제·과수화상병 등 당일 핵심 의제를 대체로 포착했다. 다만 dist 섹션의 리드가 농산물 유통 현장성보다 범산업·수출지원 성격이 강해 약했고, pest는 같은 과수화상병 축이 반복되면서 더 강한 전국 확산/위기단계 기사 선택 기회를 일부 놓쳤다. supply는 양파 과잉·저장공간 병목을 잘 짚었지만 3번 카드가 사실상 시세 보드성 기사라 묶음의 완성도는 다소 떨어진다. 최고점대(95+)를 줄 정도의 편집 완성도는 아니다.
- [high] weak_core: 중동발 충격 확산…정부, K-푸드 물류·플라스틱 고용 방어 총력 - 농산물 유통보다 범산업 대응 비중이 커 dist 대표 기사로는 초점이 흐림.
- [high] missed_opportunity: 과수화상병 위기 단계 ‘주의’→‘경계’ 상향 기사 미선정 - 전국 단위 위험도 상승을 보여주는 더 강한 앵글이 후보군에 있었음.
- [medium] theme_duplication: 과수화상병 2건 동시 채택 - 경기 첫 발생과 세종 첫 발생이 유사 축으로 반복돼 정보 효율이 낮음.
- [medium] weak_tail: [한눈에 보는 시세] 양배추, 반입량 많고 소비는 침체…‘약세늪’서 허... - 시황 보드성 성격이 강해 공급 이슈의 원인·대응 맥락이 약함.
- [medium] missed_opportunity: "가락시장 물류 선진화 속도"…파렛트 운송지원 확대 - 좋은 운영 기사지만 core보다 뒤에 놓여 섹션 핵심성이 약해짐.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
