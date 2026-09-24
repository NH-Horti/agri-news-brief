## Daily Eval (2026-06-15)
- Overall: **85.00** (pass)
- Operational: **94.92**
- Reader quality: **93.23** (capped; penalty=1.7, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **85.00** (needs_iteration, editorial_blocking_issue; editorial=85.0, operational=94.9)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=92.3, retrieval=86.9, section_fit=96.9, core=99.2, commodity=88.0
- Briefing cards: 19 / Commodity cards: 20
- Sections: supply:5/5 raw=254, policy:4/5 raw=123, dist:5/5 raw=51, pest:5/5 raw=38
- Metrics: title_unique=1.00, domain_diversity=0.79, summary_presence=1.00, summary_numeric=0.84, fresh_72h=1.00, fit_avg=4.02, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=9, commodity_active_today=15, commodity_active_today_unlinked=6, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.78, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **85.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=84.0, section_fit=83.0, core=86.0, summary=72.0, missed=80.0, noise=78.0
- Summary: 전반적으로 주요 이슈 축은 잡았지만, 공급 섹션의 잡음과 배치 오류가 크고 정책은 1건 부족합니다. dist·pest는 핵심 이슈를 대체로 맞췄으나, dist에서 유사한 일본 도매시장 기사 2건 동시 채택은 효율이 떨어집니다. raw pool이 충분한데도 공급에 연예인 챌린지·리테일성 읽을거리·기술보도성 꼬리 기사가 섞였고, 정책은 더 강한 할당관세 단독 후보가 있는데 비핵심으로 밀린 점이 감점 요소입니다.
- [high] wrong_section: 소유진·심진화부터 '흑백요리사' 셰프까지…' 양파 챌린지' 동참 - 소비촉진 이벤트성 기사로 수급 핵심성 약함.
- [medium] weak_tail: "보이면 바로 사세요"…6월 지나면 사라지는 '초여름 과일' [프라이스&] - 리테일 칼럼형으로 산업 수급 정보 밀도 낮음.
- [medium] weak_tail: 농진청, 여름 배추 수급 불안 해소한다 - 정책·기술지원 성격이 강해 공급 섹션 적합도 보통.
- [medium] underfill: 정책 섹션 4건 편성 - raw pool이 충분한데 목표 5건 미달.
- [high] missed_better_candidate: [단독]고환율 속 수입 농산물...할당관세 효과 '2년 연속' 분석한다 - 정책 파급력 높은 단독인데 비핵심 처리됨.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
