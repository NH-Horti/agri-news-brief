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
- Summary: 핵심 축은 대체로 맞았지만, 공급·정책에서 약한 꼬리 기사와 오배치가 보이고, 유통에서는 일본 도매시장 기사 중복 성격이 강합니다. 특히 정책은 원풀(123건)이 충분한데도 4건에 그쳤고, 5번째 슬롯에 넣은 CJ프레시웨이 재계약 기사는 정책 섹션에 부적합합니다. 공급도 산딸기·영동 수박 같은 생활/지역 출하성 기사보다 더 직접적인 수급·유통 구조 기사 선택 여지가 보입니다. 전반적으로 사용 가능하지만 95점대 편집 품질로 보긴 어렵습니다.
- [high] wrong_section: CJ프레시웨이, 세광푸드와 식자재 계약→동원F&B, '컨펙스' 그랑프리 - 기업 계약·산업 단신으로 정책성 부족.
- [medium] underfill: 정책 섹션 4건만 편성 - 원풀이 충분한데 목표 5건 미달.
- [high] missed_opportunity: 온라인도매시장, 왜 나랏돈 퍼주는 '곳간' 됐나 - 유통 구조 비판의 강한 전국성 기사인데 미선정.
- [medium] duplication: 오타도매시장 / 요코하마도매시장 / 토요스 도매시장 - 일본 도매시장 사례가 3건으로 과밀.
- [medium] weak_tail: "보이면 바로 사세요"…6월 지나면 사라지는 '초여름 과일' - 소매 MD형 계절 소비 기사로 수급 핵심성 약함.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
