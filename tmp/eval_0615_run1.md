## Daily Eval (2026-06-15)
- Overall: **86.00** (pass)
- Operational: **94.56**
- Reader quality: **92.87** (capped; penalty=1.7, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **86.00** (needs_iteration, editorial_blocking_issue; editorial=86.0, operational=94.6)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=90.0, retrieval=86.9, section_fit=100.0, core=87.1, commodity=96.8
- Briefing cards: 19 / Commodity cards: 22
- Sections: supply:5/5 raw=254, policy:4/5 raw=123, dist:5/5 raw=51, pest:5/5 raw=38
- Metrics: title_unique=1.00, domain_diversity=0.79, summary_presence=1.00, summary_numeric=0.63, fresh_72h=1.00, fit_avg=3.84, false_positive=0.00, hard_reader_issues=0, weak_core=0.20, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=9, commodity_active_today=15, commodity_active_today_unlinked=6, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.56, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=84.0, section_fit=86.0, core=88.0, summary=92.0, missed=80.0, noise=79.0
- Summary: 핵심 이슈는 대체로 잡았지만, 공급·정책에서 약한 꼬리 기사와 오배치가 보여 편집 완성도가 떨어진다. 특히 공급 섹션에 연예인 참여형 양파 소비 기사, 지역 출하 단신, 리테일형 산딸기 기사까지 섞이면서 수급 핵심성이 약해졌다. 정책은 후보 풀이 충분한데도 4건만 채웠고, 그중 1건은 사실상 기업 식자재 계약 뉴스라 명백한 오선정이다. 반면 dist는 물류·도매시장·수출 채널 중심으로 비교적 잘 구성됐고, pest도 화상병 확산을 중심축으로 잡은 점은 적절하다. 다만 pest 꼬리에서 우박 피해 2건이 중복감 있게 들어가고, 더 강한 전국 확산 기사나 충북 확산 해설 기사를 충분히 활용하지 못했다.
- [high] wrong_section: CJ프레시웨이, 세광푸드와 식자재 계약→동원F&B, '컨펙스' 그랑프리 - 기업 계약·홍보성 산업 기사로 농정 정책성과 무관.
- [medium] underfill: 정책 섹션 4건만 편성 - 원시 후보가 충분한데 목표 5건 미달.
- [high] missed_opportunity: 온라인도매시장, 왜 나랏돈 퍼주는 '곳간' 됐나 - 유통 구조 비판성이 큰 강한 후보를 통째로 놓침.
- [medium] weak_tail: 소유진·심진화부터 '흑백요리사' 셰프까지…' 양파 챌린지' 동참 - 연예인 소비촉진 화제성 중심으로 수급 분석 밀도 낮음.
- [medium] weak_tail: [픽! 영동] 금강 모래밭서 생산된 '양산수박' 출하 - 지역 출하 단신 성격이 강해 전국 수급 가치 낮음.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
