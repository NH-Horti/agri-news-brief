## Daily Eval (2026-10-01)
- Overall: **89.88** (warn)
- Operational: **93.80**
- Reader quality: **91.62** (capped; penalty=2.2, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **89.88** (needs_major_iteration, editorial_acceptance_gate_failed; editorial=75.0, operational=93.8)
- Scores: completeness=96.4, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=78.1, section_fit=100.0, core=77.0, commodity=87.0
- Briefing cards: 16 / Commodity cards: 21
- Sections: supply:5/5 raw=199, policy:5/5 raw=67, dist:4/5 raw=48, pest:2/2 raw=7
- Metrics: title_unique=1.00, domain_diversity=0.81, low_tier=0.12, summary_presence=1.00, summary_numeric=0.88, fresh_72h=1.00, fit_avg=3.30, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=6, commodity_active_today=12, commodity_active_today_unlinked=6, commodity_coverage=0.18, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=1.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **75.05** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 75.10; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, section_count_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 85.5 (underfilled)
- Components: article_selection=75.0, section_fit=78.0, core=70.0, summary=88.0, missed=68.0, noise=72.0
- Summary: 요약은 선명하지만 핵심 기사 우선순위와 섹션 구성이 약하다. 해외 기상기사와 지역·기업성 소재가 강한 자리를 차지했고, dist는 활용 가능한 후보가 있는데도 4건에 그쳤다.
- [moderate] weak_core: 도쿄 35일 연속 비에 '기상병' 호소…채소값도 급증 - 일본 현지 수급 전망으로 국내 농업 독자에 대한 직접성이 낮다.
- [moderate] weak_core: 2025년도 면적당 농산물 소득 7.7% 줄었다 - 전국 5300농가 조사와 경영비 상승을 담은 주요 생산경제 지표다.
- [moderate] promotional_filler: 수확 뒤 과수 수세 회복···조비, 감사비료 2종 제안 - 특정 업체 제품 제안이 중심이며 독립적인 수급 정보가 부족하다.
- [moderate] wrong_section: 계절마다 농가 덮치는 이상기후⋯강원 농업 현장 ‘비상’ - 정책 결정이나 제도보다 우박·폭염·가뭄에 따른 작물 피해가 중심이다.
- [moderate] weak_core: 계절마다 농가 덮치는 이상기후⋯강원 농업 현장 ‘비상’ - 정책 섹션의 핵심으로 삼기에는 제도적 조치가 부족하다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=19%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
