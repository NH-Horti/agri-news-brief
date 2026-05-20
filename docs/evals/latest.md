## Daily Eval (2026-05-21)
- Overall: **92.01** (pass)
- Operational: **92.01**
- Scores: completeness=81.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=88.8, section_fit=90.5, core=97.7, commodity=94.0
- Briefing cards: 13 / Commodity cards: 58
- Sections: supply:5/3 raw=156, policy:1/3 raw=104, dist:3/3 raw=41, pest:4/3 raw=70
- Metrics: title_unique=1.00, domain_diversity=0.92, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.27, false_positive=0.00, weak_core=0.00, editorial_penalty=1.7, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Components: article_selection=80.0, section_fit=76.0, core=78.0, summary=89.0, missed=77.0, noise=80.0
- Summary: 핵심 이슈인 양파 공급과잉과 과수화상병은 잘 포착했지만, 섹션 배치와 카드 구성의 균형이 아쉽다. 특히 supply에 병해충·현장지원성 기사가 섞였고, policy는 1건만 넣어 큰 정책 후보들을 놓쳤다. dist는 핵심 카드가 MOU성·홍보성에 치우쳤다. 전반적으로 읽을거리는 있으나, 편집 판단 기준으로는 ‘좋은 브리핑이지만 분명한 약점이 있는’ 수준이다.
- [high] wrong_section: [르포] "새벽마다 소독해도 속수무책"…사과산지 충주 비상 - 과수화상병 현장 르포로 pest 성격이 강함.
- [high] underfilled_section: 시설 원예 농가 경영비 절감·안정 생산 총력 지원 - policy가 1건뿐이고 더 큰 정책 후보를 놓침.
- [high] missed_opportunity: 중동發 국제곡물가 최대 12.1%↑… 농식품부 "11월까지 물량 확보" - 수입곡물·사료·가공식품 파급을 다룬 더 큰 정책 이슈.
- [medium] promotional_filler: 강릉도매시장-미스터아빠, '미래형 북상 사과 SCM 혁신 프로젝트' 업무... - MOU 발표성 기사로 실적·제도 변화보다 홍보 비중이 큼.
- [medium] promotional_filler: 마늘의무자조금관리위원회, "마늘가격 지킬 수 있어요" - 단체 메시지 전달 중심으로 검증 정보가 약함.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: policy. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=23%, pest_theme_duplicate=15%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
