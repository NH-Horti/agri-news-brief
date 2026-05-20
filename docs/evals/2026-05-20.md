## Daily Eval (2026-05-20)
- Overall: **95.54** (pass)
- Operational: **95.54**
- Scores: completeness=100.0, diversity=98.8, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=96.4, core=100.0, commodity=100.0
- Briefing cards: 16 / Commodity cards: 45
- Sections: supply:5/3 raw=150, policy:4/3 raw=83, dist:3/3 raw=51, pest:4/3 raw=55
- Metrics: title_unique=1.00, domain_diversity=0.69, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.14, false_positive=0.00, weak_core=0.00, editorial_penalty=2.8, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Components: article_selection=80.0, section_fit=78.0, core=81.0, summary=90.0, missed=79.0, noise=80.0
- Summary: 핵심 이슈인 양배추 급락, 계란·축산물 수급대책, 과수화상병 발생은 잘 잡았지만, 섹션 배치와 카드 강도에서 분명한 약점이 있다. 공급 섹션에 지역축제 물가성 기사와 광고성 저장비닐 기사가 섞였고, 유통 섹션의 코어가 단순 출하 홍보성에 치우쳤다. 병해충 섹션은 동일 주제 중복이 있으며, 정책 섹션도 실제 정책 변화보다 수급 현상 기사 비중이 있다. 후보풀에 보이는 더 적합한 유통·병해충 후속 기사 활용이 아쉬워 목표점수 95에는 못 미친다.
- [high] wrong_section: 치솟는 감자 값에 단오 물가 비상…강릉시·단오제위 안정화 안간힘 - 지역 축제 물가 기사로 전국 수급 대표성이 약함.
- [high] promotional_filler: 사과 장기저장 솔루션 제안, 숨쉬는 저장비닐 ‘그린라이트’ - 제품 소개성 홍보 기사로 뉴스 가치가 낮음.
- [high] weak_core: 청주 오송농협, ‘청원생명 맛찬동이’ 수박 본격 출하 - 단순 브랜드 출하 알림으로 유통 구조 변화 정보가 부족함.
- [medium] promotional_filler: 강원 농협 연합판매사업 협의회, 2026 산지 유통 현장투어 개최 - 견학 행사성 기사로 실질 유통 이슈 밀도가 낮음.
- [medium] duplicate_theme: “예측보다 빨랐다”…‘과수화상병’ 충주·원주서 잇따라 발생 / ‘ 과수화상병 ’ 주의보 - 같은 화상병 이슈를 유사하게 중복 소비함.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=6%, promotional_filler=12%, dist_weak_ops=6%, pest_theme_duplicate=12%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
