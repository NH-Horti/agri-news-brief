## Daily Eval (2026-05-22)
- Overall: **96.15** (pass)
- Operational: **96.15**
- Scores: completeness=89.2, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=99.6, commodity=97.2
- Briefing cards: 17 / Commodity cards: 44
- Sections: supply:4/5 raw=159, policy:4/5 raw=166, dist:4/5 raw=53, pest:5/5 raw=44
- Metrics: title_unique=1.00, domain_diversity=0.71, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.44, false_positive=0.00, weak_core=0.00, editorial_penalty=0.5, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **88.00** (target 95, needs_iteration)
- Section count gate: 97.0 (target_met)
- Components: article_selection=87.0, section_fit=85.0, core=90.0, summary=93.0, missed=82.0, noise=84.0
- Summary: 핵심 이슈 축은 대체로 맞췄다. 공급은 양파 가격 폭락·비축 지연을 잘 잡았고, 정책은 가격안정제·국회 입법을 중심으로 무게감이 있다. 병해충도 과수화상병 경계 격상과 지역 발생을 적절히 반영했다. 다만 3개 섹션이 5건 목표를 채우지 못한 데다, 공급·정책 꼬리 기사에 지역 홍보성/접수형 filler가 섞였고, 유통은 물류·수출 차질보다 약한 카드 비중이 높아 편집 완성도가 떨어진다. raw pool상 더 나은 유통/정책 후보가 보이므로 95급은 어렵다.
- [medium] underfill: 섹션 4건만 편성 - raw 후보가 충분한데 5건 목표 미달
- [high] wrong_fit: 경산시 와촌면 지역 대표 특산품 자두 본격 출하 - 단순 지역 출하 소개로 수급 이슈성이 약함
- [medium] underfill: 섹션 4건만 편성 - raw 후보가 충분한데 5건 목표 미달
- [high] promotional_filler: 정선군, 친환경농업 직불제 접수 - 지자체 접수 안내성 기사로 전국 정책 가치 낮음
- [medium] underfill: 섹션 4건만 편성 - raw 후보가 충분한데 5건 목표 미달

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
