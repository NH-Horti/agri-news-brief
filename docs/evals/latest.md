## Daily Eval (2026-07-09)
- Overall: **80.93** (warn)
- Operational: **94.10**
- Reader quality: **84.00** (capped; penalty=4.1, cap=84.0, reasons=commodity_false_link, commodity_false_link_severe, preferred_slot_underfill)
- Quality gate: **80.93** (needs_iteration, editorial_major_issue; editorial=80.7, operational=94.1)
- Scores: completeness=96.4, diversity=94.0, source=75.8, summary=96.8, freshness=100.0, retrieval=90.0, section_fit=100.0, core=83.1, commodity=93.8
- Briefing cards: 19 / Commodity cards: 14
- Sections: supply:4/5 raw=222, policy:5/5 raw=190, dist:5/5 raw=68, pest:5/5 raw=39
- Metrics: title_unique=1.00, domain_diversity=0.68, low_tier=0.21, summary_presence=1.00, summary_numeric=0.84, fresh_72h=1.00, fit_avg=4.68, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.2, commodity_weak=0.00, commodity_items=8, commodity_active_today=12, commodity_active_today_unlinked=4, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.12, commodity_pool_false_link=0.00, commodity_dominant_section=0.62, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **80.70** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 81.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=82.0, section_fit=85.0, core=83.0, summary=77.0, missed=76.0, noise=79.0
- Summary: 전반적으로 핵심 이슈인 농산물 가격 하락 대응, 온라인도매 물류, 과수화상병 예찰은 잡았지만, 원자료가 충분한데 supply가 4장에 그쳤고 dist·pest 후반부에 행사성·지역성·일반 재배관리 카드가 섞였다. 특히 dist는 더 구체적인 공판장·물류 운영 후보를 일부 놓쳤고, pest는 제목과 요약 불일치 및 명명 병해충 후보 누락이 아쉽다.
- [moderate] underfill: supply section - 원자료 222건으로 충분한데 5장 목표를 채우지 못하고 4장에 그쳤다.
- [moderate] noise: [농가월령가] 충남 멜론 의 미래 품종 다변화와 프리미엄 전략에 달렸다 - 일일 수급 브리핑보다는 칼럼성 품종전략 글로 공급 섹션 후순위 filler에 가깝다.
- [minor] duplicate_theme: 농산물 가격 폭락에 농민 울분…정부, 경영 안정 위해 '총력 대응' / 농산물 가격 하락분 지원… 가격안정제 도 입 - 가격 폭락 대응과 가격안정제 설명이 일부 중복돼 정책 섹션의 의제 폭이 좁아졌다.
- [moderate] missed_candidate: 대관령원예농협, 산지공판장 초매식 개최 - 고랭지 배추·무·감자 첫 경매와 3개월 공판장 운영이라는 구체적 유통 운영 기사였으나 누락됐다.
- [moderate] promotional_filler: 농협경제지주, 농산물 유통사업 발전 협업그룹 발대 - 발대식 중심 기사로 실제 거래·물류 변화가 아직 약해 dist 후반 카드로도 다소 느슨하다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=11%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
