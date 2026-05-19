## Daily Eval (2026-05-19)
- Overall: **90.29** (pass)
- Operational: **90.29**
- Scores: completeness=58.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=98.3, commodity=97.2
- Briefing cards: 5 / Commodity cards: 57
- Sections: supply:3/3 raw=149, policy:1/3 raw=107, dist:0/3 raw=49, pest:1/3 raw=47
- Metrics: title_unique=1.00, domain_diversity=1.00, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.85, false_positive=0.00, off_scope=0.00, story_dup=0.00, weak_core=0.00, commodity_weak=0.00, quality_penalty=0.0


### Editorial Shadow Eval
- Editorial: **72.00** (target 95, needs_major_iteration)
- Components: article_selection=68.0, section_fit=54.0, core=60.0, summary=83.0, missed=62.0, noise=50.0
- Summary: 핵심 이슈인 양파 가격 급락과 과수화상병은 잡았지만, 전체적으로 섹션 편성이 크게 흔들렸다. 유통(dist) 카드가 아예 없는데 도매시장 교육성 기사를 supply 핵심으로 올렸고, supply도 시장 수급 본류보다 행사·교육성 소재 비중이 높다. policy는 계란 수입 1건만으로는 약하며, 같은 풀에 있던 규제완화·가격안정기금 등 보완 후보를 놓쳤다. 요약문 자체는 수치와 맥락이 대체로 충실하다.
- [high] wrong_section: 동화청과, 청년농 경매 실전교육 - 도매시장 유통교육 기사로 supply보다 dist 성격이 강함.
- [high] missing_section: 유통 섹션 공백 - 가공수출·물류개선·군납 변화 등 dist 후보가 있었는데 카드가 없음.
- [medium] promotional_filler: 세종청사 햇 양파 직거래장터… 양파 값 폭락에 최대 40% 할인 - 행사 자체보다 판촉 중심이라 이슈 구조 설명이 약함.
- [high] missed_opportunity: [전국 톡톡] 전국서 갈아엎는 양파 밭‥"생산비도 못 건져" - 양파 급락의 현장성과 심각도를 더 직접적으로 보여주는 후보를 놓침.
- [high] weak_core: 계란값 안정 위해 신선란 224만개 수입... 한 판 5990원 - 정책 섹션 단독 핵심으로는 범위가 좁고 공급 기사와 경계가 흐림.
- [medium] section_balance: 정책 섹션 과소선정 - 정책 후보풀이 충분했는데 1건만 채택해 정부 대응 스펙트럼이 빈약함.
- [medium] missed_opportunity: 농식품부 규제합리화 50건 - 온라인 도매시장 참여 문턱 완화 등 업계 파급력이 큰 정책을 놓침.
- [medium] missed_opportunity: 논산 비타베리 냉동딸기, 인도네시아 첫 수출길 올라 - 가공형 수출·연중 공급체계라는 유통 의미가 뚜렷한 후보를 미반영.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: policy, dist, pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
