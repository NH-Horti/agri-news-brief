## Daily Eval (2026-05-21)
- Overall: **92.60** (pass)
- Operational: **92.60**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=88.8, section_fit=91.4, core=100.0, commodity=94.0
- Briefing cards: 14 / Commodity cards: 59
- Sections: supply:4/3 raw=153, policy:3/3 raw=101, dist:3/3 raw=38, pest:4/3 raw=72
- Metrics: title_unique=1.00, domain_diversity=0.86, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.39, false_positive=0.00, weak_core=0.00, editorial_penalty=5.2, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.00** (target 95, needs_iteration)
- Components: article_selection=82.0, section_fit=84.0, core=80.0, summary=88.0, missed=79.0, noise=81.0
- Summary: 핵심 이슈인 양파 공급과잉, 국제곡물, 과수화상병은 대체로 잘 잡았지만 섹션 간 중복된 양파 서사가 많고, 공급·유통 섹션에 지역사업·홍보성 카드가 섞였다. 특히 공급의 마늘 자조금 기사와 유통의 벤치마킹 기사는 핵심성·정보 밀도가 약하다. 원시 후보군에 보인 더 강한 대안들(양파 산지 폐기/최저생산비 요구, 밀가루 담합 후속 등)을 충분히 반영하지 못해 목표점수에는 못 미친다.
- [high] weak_core: 마늘의무자조금관리위원회, "마늘가격 지킬 수 있어요" - 자조금발 안심 메시지 중심의 홍보성 기사다.
- [high] wrong_priority: 무주군, 사과 ·포도 등 60억 규모 농산물 가격안정 지원…29일까지 신청 - 지역 신청 공고성 기사로 전국 브리핑 가치가 낮다.
- [medium] wrong_section: 충남도농기원, 시설채소 현장기술지원단 가동..."폭염 속 토마토 ·오이... - 생산기술·재배관리 성격이 강해 공급 수급 카드와 거리가 있다.
- [high] missed_opportunity: 국제 밀·대두 추가 상승 전망…정부 "8∼11월 물량 확보" - 무난한 선택이나 밀가루 담합 제재 후속이 더 강한 정책 이슈였다.
- [medium] duplication: 무안 양파 값 폭락…"캘수록 손해, 갈아엎어도 소용없다" - 공급 섹션 핵심 양파 기사와 주제가 과도하게 겹친다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=21%, pest_theme_duplicate=14%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
