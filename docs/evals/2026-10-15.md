## Daily Eval (2026-10-15)
- Overall: **79.76** (warn)
- Operational: **90.15**
- Reader quality: **86.75** (capped; penalty=3.4, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **79.76** (needs_major_iteration, editorial_major_issue; editorial=69.0, operational=90.2)
- Scores: completeness=96.4, diversity=90.7, source=96.8, summary=100.0, freshness=100.0, retrieval=79.8, section_fit=88.2, core=76.1, commodity=88.0
- Briefing cards: 19 / Commodity cards: 26
- Sections: supply:5/5 raw=305, policy:4/5 raw=93, dist:5/5 raw=65, pest:5/5 raw=19
- Metrics: title_unique=1.00, domain_diversity=0.58, low_tier=0.16, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=3.12, false_positive=0.00, hard_reader_issues=0, weak_core=0.29, editorial_penalty=1.1, commodity_weak=0.00, commodity_items=7, commodity_active_today=16, commodity_active_today_unlinked=9, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.86, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **69.05** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 70.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=70.0, section_fit=74.0, core=61.0, summary=88.0, missed=55.0, noise=68.0
- Summary: 형식과 요약은 안정적이지만 강한 후보를 놓치고 중복·현장행사성 카드가 들어갔다. 특히 과수화상병 핵심 후보 누락, dist의 APC 중복, supply 핵심 선정 오류와 policy 미충원이 품질을 낮춘다.
- [major] missed_candidate: 농진청장 "과수화상병 전체 폐원 대신 부분 폐원 검토" - 방제 기준 변경 가능성이 있는 당일 최상위 핵심 후보를 누락했다.
- [major] duplicate_story: 강릉농협 산지유통센터 스마트 APC 공모 선정 - 강원 APC 선정 카드와 동일한 59억원 사업을 반복한다.
- [major] missed_candidate: 임미애 의원 "온라인도매시장 4건 중 1건 이상거래" - 구체적인 시장 운영 문제로 dist의 가장 강한 후보인데 supply에만 배치됐다.
- [moderate] wrong_section: 내년부터 농촌에 AI 로봇 보급…수확·병해충 예찰 돕는다 - 주제가 병해충 발생·방제보다 농업기술 보급 정책에 가깝다.
- [moderate] weak_core: 농산물 값 절반이 유통 비용…온라인 도매시장도 '4건 중 1건' 이상거래 - 수급보다 유통시장 운영·국정감사 이슈이므로 supply 핵심으로는 부적절하다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=11%, dist_weak_ops=11%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
