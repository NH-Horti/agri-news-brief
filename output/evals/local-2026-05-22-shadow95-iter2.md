## Daily Eval (2026-05-22)
- Overall: **97.87** (pass)
- Operational: **97.87**
- Scores: completeness=100.0, diversity=96.7, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=99.6, core=100.0, commodity=91.3
- Briefing cards: 15 / Commodity cards: 42
- Sections: supply:3/3 raw=156, policy:4/3 raw=172, dist:3/3 raw=53, pest:5/3 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.67, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=5.00, false_positive=0.00, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=85.0, section_fit=84.0, core=88.0, summary=92.0, missed=82.0, noise=83.0
- Summary: 핵심 이슈인 양파 공급과잉·비축 지연, 가격안정제 시행, 과수화상병 발생은 잘 잡았다. 다만 dist가 가장 약하다. 물류·시장운영 기사 2개는 괜찮지만 교육성 현장견학 기사가 유통 섹션의 운영 강도를 떨어뜨렸고, 더 나은 수출·물류 후보를 일부 놓쳤다. policy도 생산자물가 기사는 농정 직접성이 약해 꼬리 기사로는 무난하나 우선도는 낮다. 전체적으로 쓸 만하지만 95점대의 날카로운 편집이라고 보긴 어렵다.
- [high] weak_tail: "도매시장 이해 높였다"…동화청과, 미래농업인 현장 교육 - 유통 운영 뉴스보다 교육행사 성격이 강하다.
- [high] missed_opportunity: K-푸드 중동 수출·물류 지원 관련 더 강한 후보 미반영 - 동일 풀에 수출 실적·우회 운송·바우처 지원을 더 구체적으로 담은 후보가 있었다.
- [medium] section_weakness: 중동발 충격 확산…정부, K-푸드 물류·플라스틱 고용 방어 총력 - 농식품 물류보다 산업 전반·고용 방어 비중이 섞여 초점이 분산된다.
- [medium] weak_tail: 중동發 원자재 충격 현실화···4월 생산자물가 28년 만에 최대 상승 - 거시물가 기사로 농정 직접성이 낮다.
- [medium] missed_opportunity: 원주 예방약제 미살포·보상 감경 검토 기사 미선정 - 화상병 대응의 책임성과 현장 교훈을 보여주는 후속성이 있었다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
