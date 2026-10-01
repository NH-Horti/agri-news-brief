## Daily Eval (2026-09-28)
- Overall: **87.67** (warn)
- Operational: **94.39**
- Reader quality: **90.16** (clear; penalty=4.2, cap=100.0, reasons=clear)
- Quality gate: **87.67** (needs_major_iteration, editorial_major_issue; editorial=77.0, operational=94.4)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=90.0, retrieval=90.0, section_fit=100.0, core=97.8, commodity=81.9
- Briefing cards: 20 / Commodity cards: 39
- Sections: supply:5/5 raw=347, policy:5/5 raw=204, dist:5/5 raw=65, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.77, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.4, commodity_weak=0.00, commodity_items=9, commodity_active_today=18, commodity_active_today_unlinked=9, commodity_coverage=0.27, commodity_strict_link=0.78, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.78, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **77.05** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 78.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=76.0, section_fit=83.0, core=72.0, summary=91.0, missed=65.0, noise=78.0
- Summary: 형식과 요약은 안정적이고 섹션별 5건도 충족했다. 그러나 정책·유통에서 원자료상 더 강한 최신 기사를 놓치고 지역 행사·단순 안내를 채웠으며, 일부 코어 지정도 우선순위가 뒤바뀌었다.
- [major] missed_candidate: 가락시장 파렛트 출하 의무화 확대…느타리버섯·봄동·제주당근 대상 - 물류비와 하역 효율에 직접 영향을 주는 구체적 운영 변화인데 단순 휴장 안내보다 우선순위가 높다.
- [moderate] missed_candidate: 성수품 공급 늘리고 할인지원은 확대…희비 엇갈린 추석 장바구니 물가 - 정부 공급·할인지원 효과와 품목별 가격을 함께 다룬 최신 고적합 기사다.
- [moderate] weak_core: [프리즘] 소비자·농가도 웃게 할 농축산물 할인 지원 - 의견 칼럼이어서 최신 정책 집행·예산 기사보다 코어 근거가 약하다. 코어에서 내려야 한다.
- [moderate] weak_core: 함평군, '현장 밀착 상담'... 벼멸구 방제부터 폭염 안전까지 총력 - 6개월간의 포괄적 상담 실적 중심으로 현재 병해충 위험 신호가 약하다. 코어에서 내려야 한다.
- [moderate] wrong_section: 가락몰 차례상 대형마트보다 21.6% 저렴 - 정책 변화보다 판매 채널별 가격 경쟁력을 다룬 유통·소비 기사에 가깝다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
