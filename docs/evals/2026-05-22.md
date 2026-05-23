## Daily Eval (2026-05-22)
- Overall: **98.17** (pass)
- Operational: **98.17**
- Scores: completeness=100.0, diversity=96.7, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=99.4, commodity=97.2
- Briefing cards: 12 / Commodity cards: 44
- Sections: supply:3/3 raw=161, policy:3/3 raw=168, dist:3/3 raw=54, pest:3/3 raw=44
- Metrics: title_unique=1.00, domain_diversity=0.67, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.86, false_positive=0.00, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Section count gate: 100.0 (target_met)
- Score calibration: 88.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=87.0, section_fit=90.0, core=86.0, summary=93.0, missed=84.0, noise=89.0
- Summary: 전반적으로 당일 핵심 농정·수급 이슈는 잘 잡았지만, 양파 기사 과밀과 dist·pest의 코어 선정이 다소 약하다. supply는 양파 가격폭락과 비축지연을 적중했으나 3번째 카드가 사실상 중복 보강에 머물렀다. policy는 가격안정제와 국회 입법 정리가 탄탄하지만 농협 개혁안은 중요도는 있어도 농정 독자 체감상 한 단계 아래다. dist는 가락시장 파렛트 지원은 section 적합하나 코어로는 다소 작고, 중동 물류 기사 2건은 서로 중복된다. pest는 화상병 경계 상향을 잡은 점은 좋지만 원주 단일농가 미살포 건을 최상위 코어로 둔 것은 전국 확산 국면 대비 무게가 약하다. 원시 후보군에 경기 첫 발생, 충북 현장진단실 가동 등 더 좋은 보강 선택지가 보였다.
- [medium] duplication: 햇 양파 공급과잉에 가격 급락…정부, 수출 확대로 돌파구 모색 - 앞선 두 양파 기사와 쟁점이 크게 겹친다.
- [medium] weak_core: "가락시장 물류 선진화 속도"…파렛트 운송지원 확대 - 운영성은 맞지만 전국 유통 핵심뉴스로는 임팩트가 약하다.
- [medium] duplication: K-푸드는 "전쟁 영향? 글쎄요"…중동 물류난에도 GCC 수출 37.6%↑ - 다음 dist 기사와 사실상 같은 중동 물류 축이다.
- [medium] duplication: 중동발 충격 확산…정부, K-푸드 물류·플라스틱 고용 방어 총력 - 앞 기사와 주제 중복에 농업 외 산업 내용이 섞인다.
- [medium] weak_core: 원주시 “ 과수화상병 농가, 예방 약제 미살포” - 행정처분성 지역 단신으로 전국 확산 이슈보다 무게가 떨어진다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
