## Daily Eval (2026-05-29)
- Overall: **84.00** (warn)
- Operational: **88.98**
- Quality gate: **84.00** (needs_iteration, editorial_below_target; editorial=84.0, operational=89.0)
- Scores: completeness=96.4, diversity=98.4, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=91.2, core=100.0, commodity=98.5
- Briefing cards: 19 / Commodity cards: 25
- Sections: supply:5/5 raw=119, policy:5/5 raw=121, dist:4/5 raw=67, pest:5/5 raw=35
- Metrics: title_unique=1.00, domain_diversity=0.68, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.21, false_positive=0.05, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, semantic_penalty=6.3


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=82.0, section_fit=81.0, core=86.0, summary=91.0, missed=78.0, noise=79.0
- Summary: 전반적으로 당일 핵심 이슈인 양파 공급과잉·수급안정, 과수화상병 확산, 온라인도매시장 활성화는 포착했지만, 기사 선별은 발행용 수준보다 한 단계 아래다. 공급과 정책 섹션은 양파 이슈 중복과 약한 꼬리 기사 비중이 크고, 유통은 4건으로 소프트 폴백에 그친 데다 지역 출하 홍보성 중복 카드 2건이 크게 감점 요인이다. 원시 후보군에 더 나은 대체재가 있었는데도 일부 약한 선택이 남아 있어 95점대는 어렵다.
- [medium] underfill: 유통 섹션 4건만 편성 - raw 후보가 충분한데 목표 5건 미달.
- [high] duplicate: '청원생명수박' 출하 기사 2건 중복 - 같은 행사·같은 내용의 지역 출하 기사 중복 편성.
- [high] filler: 청원생명수박 출하 관련 2건 - 유통 핵심보다 지역 출하 홍보 성격이 강함.
- [high] missed_opportunity: 남원시조합공동사업법인 기사 미선정 - 생산유통통합조직 운영 기사로 유통 섹션 적합도가 높음.
- [medium] missed_opportunity: 양파 수출확대 추진 기사 미선정 - 당일 정책 실행안인데 성과 브리핑성 기사보다 실무성이 높음.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 5%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
