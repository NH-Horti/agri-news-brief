## Daily Eval (2026-05-22)
- Overall: **98.10** (pass)
- Operational: **98.10**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=95.4, core=100.0, commodity=94.0
- Briefing cards: 14 / Commodity cards: 43
- Sections: supply:3/3 raw=156, policy:4/3 raw=172, dist:3/3 raw=53, pest:4/3 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.71, summary_presence=1.00, summary_numeric=0.93, fresh_72h=1.00, fit_avg=5.06, false_positive=0.00, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **85.00** (target 95, needs_iteration)
- Components: article_selection=84.0, section_fit=81.0, core=87.0, summary=91.0, missed=83.0, noise=80.0
- Summary: 양파 수급 이슈와 가격안정제도, 과수화상병은 잘 잡았지만 유통 섹션이 가장 약하다. 가락시장 파렛트 지원은 실무성은 있으나 핵심성은 낮고, 대구·경북 협력·무안군 직거래는 지역성·행사성이 강해 지면 가치가 떨어진다. 반면 보이는 후보 중 세종 첫 과수화상병, 충북 현장진단실, K-푸드 중동 물류 대응 등 더 전국성 있는 대안이 있었다. 정책·공급 요약은 대체로 유용하다.
- [high] weak_core: "가락시장 물류 선진화 속도"…파렛트 운송지원 확대 - 실무 공지 성격이 강해 유통 핵심 뉴스로는 약하다.
- [high] promotional_filler: "대구·경북 농산물 유통협력 강화" - 간담회성 지역 협력 기사로 정보가 얕다.
- [medium] promotional_filler: 무안군, ' 양파 100톤' 수도권 직거래로 판로 뚫었다 - 지자체 소비촉진 행사 성격이 강하다.
- [medium] missed_opportunity: 농진청, 과수화상병 확산 차단... 세종서 첫 과수화상병 확진…위기단계... - 세종 첫 발생과 위기단계 상향은 전국성 더 크다.
- [medium] missed_opportunity: 충북농기원, 과수화상병 차단 총력 - 충북 발생·현장진단실 가동은 방제 실무성이 높다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
