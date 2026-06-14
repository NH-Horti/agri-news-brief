## Daily Eval (2026-05-22)
- Overall: **97.92** (pass)
- Operational: **97.92**
- Scores: completeness=100.0, diversity=96.7, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=100.0, commodity=91.3
- Briefing cards: 12 / Commodity cards: 42
- Sections: supply:3/3 raw=156, policy:3/3 raw=172, dist:3/3 raw=53, pest:3/3 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.67, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.86, false_positive=0.00, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Section count gate: 100.0 (target_met)
- Score calibration: 88.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=87.0, section_fit=90.0, core=86.0, summary=84.0, missed=83.0, noise=91.0
- Summary: 전반적으로 당일 핵심 농정·수급 이슈를 잘 잡았고 섹션 수량도 충족했다. 다만 공급 섹션이 양파 3건으로 과밀해 중복감이 크고, dist는 물류·시장운영 핵심성이 약한 카드가 섞였다. pest는 과수화상병 경보 상향을 잡은 점은 좋지만, 더 강한 발생 확산 기사 일부를 놓쳤다. 운영 점수와 달리 편집적으로는 핵심 우선순위와 섹션 내 구성 균형에서 아쉬움이 있어 95점대는 어렵다.
- [high] duplication: 햇 양파 공급과잉에 가격 급락…정부, 수출 확대로 돌파구 모색 - 양파 3건째로 앞선 2건과 논점 중복이 크다.
- [high] missed_opportunity: [한눈에 보는 시세] 양배추, 반입량 많고 소비는 침체…‘약세늪’서 허... - 원물 시세 급락을 수치로 보여주는 더 강한 대체 후보가 있었다.
- [medium] section_fit: K-푸드는 "전쟁 영향? 글쎄요"…중동 물류난에도 GCC 수출 37.6%↑ - 수출 실적 중심이라 유통·물류 장애의 구체성이 약하다.
- [medium] section_fit: 중동발 충격 확산…정부, K-푸드 물류·플라스틱 고용 방어 총력 - 농식품 물류보다 산업 전반·고용 비중이 커 dist 집중도가 떨어진다.
- [medium] missed_opportunity: 화성서 올해 첫 경기도 과수화상병 발생…도농기원 “확산 차단 총력” - 권역 첫 발생 기사인데 선정에서 빠져 지역 확산 강도가 약해졌다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
