## Daily Eval (2026-06-15)
- Overall: **84.00** (warn)
- Operational: **94.56**
- Reader quality: **92.87** (capped; penalty=1.7, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **84.00** (needs_iteration, editorial_blocking_issue; editorial=84.0, operational=94.6)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=90.0, retrieval=86.9, section_fit=100.0, core=87.1, commodity=96.8
- Briefing cards: 19 / Commodity cards: 22
- Sections: supply:5/5 raw=254, policy:4/5 raw=123, dist:5/5 raw=51, pest:5/5 raw=38
- Metrics: title_unique=1.00, domain_diversity=0.79, summary_presence=1.00, summary_numeric=0.63, fresh_72h=1.00, fit_avg=3.84, false_positive=0.00, hard_reader_issues=0, weak_core=0.20, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=9, commodity_active_today=15, commodity_active_today_unlinked=6, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.56, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=82.0, section_fit=86.0, core=88.0, summary=91.0, missed=78.0, noise=79.0
- Summary: 전반적으로 읽을 만한 브리핑이지만, 고득점감은 아니다. 핵심축인 정책의 농자재 가격 압박, 유통의 화훼공판장·도매시장 물류 기능, 병해충의 과수화상병 확산은 방향이 맞다. 다만 공급 섹션에 연예인 양파 챌린지·산딸기 소비형 기사·지역 수박 출하가 섞이며 밀도가 떨어졌고, 정책은 raw pool이 충분한데도 4건만 채워 선호 개수를 못 맞췄다. 또 policy에 CJ프레시웨이 재계약 기사를 넣은 것은 명백한 오분류다. dist는 일본 도매시장 기사 2건이 유사해 중복감이 있고, pest는 화상병 강세 속에 우박 피해 2건을 같이 넣어 테마 중복성도 남았다.
- [high] wrong_section: CJ프레시웨이, 세광푸드와 식자재 계약→동원F&B, '컨펙스' 그랑프리 - 정책 이슈가 아닌 기업 계약 기사다.
- [medium] underfill: 정책 섹션 4건 편성 - raw 후보가 충분한데 5건 목표를 못 채웠다.
- [medium] weak_selection: 소유진·심진화부터 '흑백요리사' 셰프까지…' 양파 챌린지' 동참 - 소비촉진 화제성은 있으나 수급 본류 정보가 약하다.
- [medium] weak_selection: [픽! 영동] 금강 모래밭서 생산된 '양산수박' 출하 - 지역 출하 단신으로 전국 수급 의미가 약하다.
- [medium] missed_opportunity: [산지 확대경] 천도 복숭아 작황 ‘맑음’…남은 가격 변수는 ‘장마’ - 더 직접적인 작황·가격 변수 기사인데 미선정됐다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
