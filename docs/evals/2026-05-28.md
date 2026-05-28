## Daily Eval (2026-05-28)
- Overall: **86.81** (pass)
- Operational: **86.81**
- Scores: completeness=92.8, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.0, section_fit=90.7, core=100.0, commodity=97.4
- Briefing cards: 18 / Commodity cards: 37
- Sections: supply:5/5 raw=149, policy:4/5 raw=93, dist:4/5 raw=34, pest:5/5 raw=51
- Metrics: title_unique=1.00, domain_diversity=0.94, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=4.94, false_positive=0.06, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.06, semantic_penalty=6.7


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 96.0 (soft_fallback)
- Components: article_selection=79.0, section_fit=78.0, core=74.0, summary=90.0, missed=76.0, noise=77.0
- Summary: 전반적으로 당일성·요약 품질은 양호하지만, 핵심 기사 선정이 약하고 섹션별 기사 고르기가 편향됐다. 공급은 홍보성 양파 기사와 군 단위 씨감자 성과가 핵심·후미를 잠식했고, 유통은 판촉·출하식 비중이 높아 운영성 있는 유통 기사보다 약했다. 병해충은 실제 확산·위기 상향 기사보다 예방·지원성 기사에 무게를 둔 점이 아쉽다. 정책·유통이 4건으로 소프트 폴백에 머문 점도 95점대 평가를 막는다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 소비홍보성 기사로 수급 핵심 이슈 기사보다 약하다.
- [high] missed_opportunity: 과잉 양파 '수매'·부족 계란 '수입'…정부 "6~7월 물가 안정 총력" - 당일 수급 핵심 정책 기사인데 공급 섹션에서 놓쳤다.
- [medium] filler: 괴산군 원원종 감자 생산 목표 초과 달성 - 지역 성과성 보드 기사로 전국 독자 효용이 낮다.
- [high] weak_core: 논산 성동농협, 수도권서 수박·방울 토마토 판촉전 ‘대박’…전량 매진 - 로컬 판촉 성과 기사로 유통 운영·구조 기사보다 무게가 약하다.
- [medium] section_fit: 완주 삼례 농협 , 명품 흑피수박 ‘블랙위너’ 본격 출하 - 출하식·품종 홍보 성격이 강해 유통 섹션 적합성이 제한적이다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1), dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 6%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 6%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
