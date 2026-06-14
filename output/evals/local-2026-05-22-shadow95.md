## Daily Eval (2026-05-22)
- Overall: **94.33** (pass)
- Operational: **94.33**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=95.9, core=93.4, commodity=91.3
- Briefing cards: 15 / Commodity cards: 42
- Sections: supply:3/3 raw=156, policy:4/3 raw=172, dist:3/3 raw=53, pest:5/3 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.73, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=5.06, false_positive=0.00, weak_core=0.14, editorial_penalty=3.2, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **88.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=87.0, section_fit=90.0, core=89.0, summary=94.0, missed=84.0, noise=83.0
- Summary: 전반적으로 당일 농정·수급 핵심 의제는 잘 잡았지만, dist와 pest에서 지역성·공지성 꼬리 기사가 많아 편집 밀도가 떨어진다. 양파 수급난, 가격안정제도, 과수화상병은 적절한 축이었으나 dist 코어는 ‘수출 호조’ 자체보다 전쟁발 물류 차질 대응 기사로 더 날카롭게 잡을 수 있었고, pest는 같은 화상병 지역 대응 기사 중복이 과했다. 높은 완성도이지만 눈에 보이는 더 나은 후보를 일부 놓쳐 95점대는 어렵다.
- [high] weak_core: 중동전쟁에도 'K푸드 호조'…중동 수출 37.6% 늘어 - 호조 실적 위주라 분배·물류 리스크 포착이 약하다.
- [high] missed_opportunity: 중동발 충격 확산…정부, K-푸드 물류·플라스틱 고용 방어 총력 - 전쟁발 물류 부담과 정부 대응이 더 직접적이다.
- [medium] promotional_filler: 무안군, ' 양파 100톤' 수도권 직거래로 판로 뚫었다 - 지자체 판촉성 직거래 행사 성격이 강하다.
- [medium] missed_opportunity: [동화청과 유통교육] "맛·품질은 기본…소비자 선택 기준까지 설계 필... - 현장 유통 구조·판매 기준 설명이 꼬리 기사로 더 유용하다.
- [medium] theme_duplication: 충북농기원, 과수화상병 차단 총력 - 화상병 대응 기사 반복으로 정보 증가폭이 작다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=7%, pest_theme_duplicate=7%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
