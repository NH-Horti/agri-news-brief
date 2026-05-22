## Daily Eval (2026-05-22)
- Overall: **94.15** (pass)
- Operational: **94.15**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=87.5, section_fit=95.4, core=100.0, commodity=94.0
- Briefing cards: 14 / Commodity cards: 43
- Sections: supply:3/3 raw=160, policy:4/3 raw=170, dist:3/3 raw=52, pest:4/3 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.71, summary_presence=1.00, summary_numeric=0.93, fresh_72h=1.00, fit_avg=5.23, false_positive=0.00, weak_core=0.00, editorial_penalty=4.0, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.00** (target 95, needs_iteration)
- Components: article_selection=84.0, section_fit=78.0, core=83.0, summary=90.0, missed=82.0, noise=79.0
- Summary: 양파 수급 이슈와 과수화상병 흐름은 대체로 잘 잡았지만, 정책·유통 섹션에서 기사 성격이 흐려졌고 핵심 기사 우선순위도 아쉽다. 특히 정책 섹션은 농산물가격안정제도 시행 기사보다 농협 개혁안을 더 강한 코어로 둔 판단이 약했고, 유통 섹션은 비유통성 기사와 지자체 판촉성 기사가 섞여 완성도가 떨어진다.
- [high] missed_opportunity: 농산물가격안정제도 8월 시행…“평균가격, 경영비 밑돌땐 차액 지원” - 정책 영향력이 가장 큰데 비코어 처리됐다.
- [high] weak_core: “농협, 직선제 받겠다”…강호동 회장 '진짜 농협' 개혁안 발표 - 농정 핵심보다 기관 거버넌스 성격이 강하다.
- [high] wrong_section: “스마트팜·신품종 보급…품목맞춤형 접근 필요” - 유통보다 기후대응·생산기반 정책 기사다.
- [medium] promotional_filler: 무안군, ' 양파 100톤' 수도권 직거래로 판로 뚫었다 - 지자체 소비촉진 보도자료 성격이 짙다.
- [medium] weak_core: "가락시장 물류 선진화 속도"…파렛트 운송지원 확대 - 실무성은 있으나 섹션 대표 코어로는 임팩트가 약하다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=14%, pest_theme_duplicate=14%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
