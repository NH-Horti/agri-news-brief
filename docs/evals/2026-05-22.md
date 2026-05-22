## Daily Eval (2026-05-22)
- Overall: **94.71** (pass)
- Operational: **94.71**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=99.4, core=100.0, commodity=94.0
- Briefing cards: 14 / Commodity cards: 43
- Sections: supply:3/3 raw=158, policy:4/3 raw=171, dist:3/3 raw=53, pest:4/3 raw=42
- Metrics: title_unique=1.00, domain_diversity=0.86, summary_presence=1.00, summary_numeric=0.93, fresh_72h=1.00, fit_avg=5.39, false_positive=0.00, weak_core=0.00, editorial_penalty=3.9, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **87.00** (target 95, needs_iteration)
- Components: article_selection=85.0, section_fit=88.0, core=84.0, summary=92.0, missed=83.0, noise=86.0
- Summary: 전반적으로 양파 수급난과 과수화상병 확산 등 당일 핵심 농정 이슈는 잘 포착했다. 다만 dist 섹션에 판촉성·기관발 기사 비중이 있고, policy는 거시 해설성 기사보다 더 직접적인 농정/입법 후보를 놓쳤다. 공급 섹션도 양파 이슈가 강하지만 중복감이 있어 더 구조적인 공급 기사로 균형을 보완할 여지가 있다.
- [high] wrong_priority: 슈퍼 엘리뇨·이란전쟁 장기화...'애그플레이션' 시대 오나 - 거시 해설형으로 농정 직접성 부족.
- [high] missed_opportunity: ‘농업민생’ 입법에 여야 합심…농협법·농지법 개정 난제 산적 - 정책 섹션 톱감인데 미선정.
- [high] promotional: 농협 유통 하나로마트, '매실' 본격출하!..사전 예약 중 - 예약판매 홍보성 강하고 뉴스 가치 약함.
- [medium] weak_core: "가락시장 물류 선진화 속도"…파렛트 운송지원 확대 - 기관 계획 발표 성격이 강해 파급력 제한.
- [medium] promotional: 무안군, ' 양파 100톤' 수도권 직거래로 판로 뚫었다 - 지자체 판촉성 캠페인 기사에 가깝다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=7%, pest_theme_duplicate=14%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
