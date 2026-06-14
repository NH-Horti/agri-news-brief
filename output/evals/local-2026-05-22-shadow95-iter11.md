## Daily Eval (2026-05-22)
- Overall: **97.92** (pass)
- Operational: **97.92**
- Scores: completeness=100.0, diversity=96.7, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=100.0, commodity=91.3
- Briefing cards: 12 / Commodity cards: 42
- Sections: supply:3/3 raw=156, policy:3/3 raw=172, dist:3/3 raw=53, pest:3/3 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.67, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.86, false_positive=0.00, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=86.0, core=82.0, summary=78.0, missed=80.0, noise=88.0
- Summary: 전반적으로 양파 수급난·가격안정제도·과수화상병 경계 상향 등 당일 핵심 의제를 상당수 포착했지만, dist 섹션의 코어 선택이 약하고 pest에서도 더 강한 발생 기사 대신 무난한 지역 대응 기사가 들어가 점수가 깎인다. supply는 양파 과잉·창고 적체를 입체적으로 잡은 점이 좋지만 3번 카드가 2번과 사실상 같은 정부 대응 축을 반복한다. policy는 가장 안정적이나 농협 개혁안은 중요도 대비 검증·파급 해설이 약한 매체를 tail로 쓴 점이 아쉽다. 전체적으로 실사용 가능하나, raw pool에 보이는 더 강한 후보를 몇 건 놓쳐 95점대 평가는 어렵다.
- [high] weak_core: "가락시장 물류 선진화 속도"…파렛트 운송지원 확대 - 운영 기사이긴 하나 전국급 충격 대비 임팩트가 약한 코어다.
- [high] missed_opportunity: 충북농기원, 과수화상병 차단 총력 - 세종 첫 발생·경기 첫 발생 기사보다 전국성 뉴스 가치가 약하다.
- [medium] redundancy: 햇 양파 공급과잉에 가격 급락…정부, 수출 확대로 돌파구 모색 - 앞선 양파 비축·폐기 기사와 대응 포인트가 겹친다.
- [medium] missed_opportunity: 전체 섹션 구성 - raw pool에 양배추 약세 시세 기사가 있어 품목 분산 기회가 있었다.
- [medium] section_fit: 중동발 충격 확산…정부, K-푸드 물류·플라스틱 고용 방어 총력 - 농식품 물류보다 산업·고용 일반론 비중이 섞였다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
