## Daily Eval (2026-07-09)
- Overall: **82.71** (warn)
- Operational: **94.35**
- Reader quality: **84.00** (capped; penalty=4.1, cap=84.0, reasons=commodity_false_link, commodity_false_link_severe, preferred_slot_underfill)
- Quality gate: **82.71** (needs_iteration, editorial_acceptance_gate_failed; editorial=82.8, operational=94.3)
- Scores: completeness=96.4, diversity=94.0, source=75.8, summary=98.4, freshness=100.0, retrieval=90.0, section_fit=100.0, core=83.1, commodity=93.8
- Briefing cards: 19 / Commodity cards: 14
- Sections: supply:4/5 raw=222, policy:5/5 raw=190, dist:5/5 raw=68, pest:5/5 raw=39
- Metrics: title_unique=1.00, domain_diversity=0.68, low_tier=0.21, summary_presence=1.00, summary_numeric=0.84, fresh_72h=1.00, fit_avg=4.68, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.2, commodity_weak=0.00, commodity_items=8, commodity_active_today=12, commodity_active_today_unlinked=4, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.12, commodity_pool_false_link=0.00, commodity_dominant_section=0.62, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.85** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 83.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, operational_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=85.0, section_fit=86.0, core=84.0, summary=78.0, missed=80.0, noise=82.0
- Summary: 전반적으로 핵심 가격·정책·물류 이슈는 잡았지만, 공급 1건 부족과 일부 약한 보충 카드가 목표 품질을 낮췄다. 정책은 물가·가격안정 축이 강하나 중복감이 있고, 유통은 온라인도매 물류와 가락시장 휴업이 좋지만 로컬 협약·행사성 꼬리가 섞였다. 병해충은 과수화상병과 사과 병해 정보는 적절하나 멜론 생육관리 등 섹션 적합도가 낮은 카드가 있다. 일부 요약은 원문 긁기 흔적과 문장 훼손이 보여 독자 효용을 떨어뜨린다.
- [moderate] underfill: 공급 섹션 4건 편성 - raw 후보가 충분한데 목표 5건을 채우지 못했다.
- [moderate] promotional_filler: [농가월령가] 충남 멜론 의 미래 품종 다변화와 프리미엄 전략에 달렸다 - 칼럼성·전략 홍보 성격이 강하고 당일 수급 뉴스성이 약하다.
- [moderate] weak_core: 농지조사·CPTPP·수확기 쌀값…하반기 농업정책 변수 - 하반기 전망성 기사로 당일 정책 실행·현장 영향의 긴급성이 낮다.
- [minor] duplicate_theme: 농산물 가격 폭락에 농민 울분…정부, 경영 안정 위해 '총력 대응' - 가격 폭락·물가 대응·가격안정제 카드가 한 섹션에 과밀하다.
- [moderate] missed_candidate: 대관령원예농협, 산지공판장 초매식 개최 - 고랭지 배추·무·감자 첫 경매와 공판장 운영이라는 구체 유통성이 selected 로컬 협약보다 강하다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=11%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
