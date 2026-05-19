## Daily Eval (2026-05-19)
- Overall: **49.79** (fail)
- Operational: **49.79**
- Scores: completeness=58.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=98.3, commodity=97.2
- Briefing cards: 5 / Commodity cards: 57
- Sections: supply:3/3 raw=145, policy:1/3 raw=110, dist:0/3 raw=49, pest:1/3 raw=47
- Metrics: title_unique=1.00, domain_diversity=1.00, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.47, false_positive=0.00, off_scope=0.00, story_dup=0.00, weak_core=0.00, commodity_weak=0.00, quality_penalty=40.5


### Editorial Shadow Eval
- Editorial: **54.00** (target 95, needs_major_iteration)
- Components: article_selection=46.0, section_fit=40.0, core=38.0, summary=74.0, missed=30.0, noise=45.0
- Summary: 핵심 이슈를 제대로 집지 못한 편집이다. 공급 섹션의 코어가 행사성·교육성 기사로 빗나갔고, 유통(dist) 섹션이 통째로 비어 있는 반면 더 적합한 후보들이 풀에 있었다. 정책·병해충은 그나마 의미 있는 현안이 들어갔지만, 전체적으로 농가·시장 영향이 큰 기사보다 홍보성·가벼운 소비 기사에 우선순위를 준 점이 크게 감점된다.
- [high] wrong_section: 동화청과, 청년농 경매 실전교육 - 수급 이슈가 아닌 교육·홍보성 도매시장 기사다.
- [high] weak_core: 동화청과, 청년농 경매 실전교육 - 농가 피해·가격 급변보다 파급력이 약한 행사 기사다.
- [high] missed_opportunity: [전국 톡톡] 전국서 갈아엎는 양파 밭‥"생산비도 못 건져" - 같은 날 가장 강한 현장형 수급 기사인데 미선정됐다.
- [high] missing_section: 유통 섹션 공란 - 가락시장 물류·냉동딸기 수출 등 적합 후보가 있었는데 비웠다.
- [medium] missed_opportunity: 논산 비타베리 냉동딸기, 인도네시아 첫 수출길 올라 - 판로 다변화·가공수출 구조 전환 의미가 뚜렷했다.
- [medium] missed_opportunity: 서울시공사, 물류 선진화 위해 순회수집 운송지원 확대 - 도매시장 물류개선이라는 정통 유통 기사였다.
- [medium] noise: 벌써 3만 원 돌파라니 무섭다...마트 갔다가 수박 가격 보고 깜짝 놀란... - 제목이 자극적이고 소비자 체감 기사 성격이 강하다.
- [medium] section_fit: 계란값 안정 위해 신선란 224만개 수입... 한 판 5990원 - 정책성은 있으나 단일 유통조치 중심으로 정책 폭이 좁다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: policy, dist, pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
