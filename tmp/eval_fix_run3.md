## Daily Eval (2026-06-15)
- Overall: **92.13** (pass)
- Operational: **94.92**
- Reader quality: **93.23** (capped; penalty=1.7, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **92.13** (needs_iteration, editorial_below_target_bounded_penalty; editorial=84.0, operational=94.9)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=92.3, retrieval=86.9, section_fit=96.9, core=99.2, commodity=88.0
- Briefing cards: 19 / Commodity cards: 20
- Sections: supply:5/5 raw=254, policy:4/5 raw=123, dist:5/5 raw=51, pest:5/5 raw=38
- Metrics: title_unique=1.00, domain_diversity=0.79, summary_presence=1.00, summary_numeric=0.84, fresh_72h=1.00, fit_avg=4.02, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=9, commodity_active_today=15, commodity_active_today_unlinked=6, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.78, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=82.0, section_fit=83.0, core=86.0, summary=72.0, missed=79.0, noise=80.0
- Summary: 전반적으로 주요 이슈 축은 잡았지만, 공급 섹션의 연예인 챌린지·리테일 칼럼 같은 약한 카드와 유통 섹션의 일본 도매시장 중복성, 병해충 섹션의 우박 기사 투입이 품질을 깎았다. 정책은 4건으로 소프트 폴백에 그쳤고, raw pool상 5건 채우기는 가능했는데 더 강한 할당관세·온라인도매시장 비판 기사 등을 충분히 활용하지 못했다. 핵심 기사들은 대체로 맞지만, 섹션별 꼬리 카드의 편집 강도가 약하다.
- [high] promotional_filler: 소유진·심진화부터 '흑백요리사' 셰프까지…' 양파 챌린지' 동참 - 연예인 참여 소비촉진은 정보가치 낮은 홍보성 기사.
- [medium] weak_tail: "보이면 바로 사세요"…6월 지나면 사라지는 '초여름 과일' [프라이스&] - 대형마트 MD 칼럼형 소비정보로 수급 핵심성 약함.
- [high] missed_opportunity: 수입품 할당관세 상시화 불가피... 먹거리 품목별 도입효과 살핀다 - 비슷한 주제의 더 강한 단독 후보가 있었는데 약한 후속 기사 선택.
- [medium] underfill: 정책 섹션 4건 편성 - raw candidates가 충분한데 5건을 못 채움.
- [medium] duplicate_theme: [일본 도매시장, 경계를 허물다] 저장·소분·가공·배송까지…무한 변... - 같은 일본 도매시장 물류 기사와 결이 겹쳐 새로움이 약함.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
