## Daily Eval (2026-08-12)
- Overall: **84.62** (warn)
- Operational: **94.12**
- Reader quality: **92.62** (clear; penalty=1.5, cap=100.0, reasons=clear)
- Quality gate: **84.62** (needs_major_iteration, editorial_major_issue; editorial=65.0, operational=94.1)
- Scores: completeness=100.0, diversity=92.0, source=60.0, summary=100.0, freshness=100.0, retrieval=88.1, section_fit=100.0, core=80.2, commodity=88.0
- Briefing cards: 20 / Commodity cards: 71
- Sections: supply:5/5 raw=325, policy:5/5 raw=120, dist:5/5 raw=63, pest:5/5 raw=47
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.25, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=3.54, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=10, commodity_active_today=21, commodity_active_today_unlinked=11, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.80, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **65.05** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 66.40; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=4, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=66.0, section_fit=64.0, core=56.0, summary=86.0, missed=55.0, noise=66.0
- Summary: 형식과 카드 수는 충족했지만, 수급·물가 소재가 과도하게 반복되고 정책·유통 섹션의 핵심 선정이 약하다. 특히 유통의 사과 시세와 병해충의 작물별 위험 기사를 놓치고 지역성·홍보성 꼬리기사를 다수 채택했다.
- [major] duplicate_theme: "배로 뛰었다" 줄줄이 오른 가격 …공포의 '히트플레이션' - 같은 섹션의 정부 가격안정·비축 기사들과 폭염 채소값 주제가 반복되며 관측도 충돌한다.
- [moderate] promotional_filler: 상주 경천대 캠벨얼리 포도 '첫 출하' - 지역 작목반 첫 출하 홍보 성격이 강하고 전국 수급 영향이 작다.
- [major] weak_core: 영양군의회, 고추재배농가 생존권 보장 건의문 등 채택 - 구체적 제도 변화가 없는 지역 의회 건의문으로 정책 핵심성이 부족하다.
- [moderate] wrong_section: 납품대금 미정산 되풀이… 농가 고통 ‘현재진행형’ - 유통업체 정산과 산지출하조직 피해는 정책보다 유통 운영 이슈에 가깝다.
- [major] missed_candidate: [한눈에 보는 시세] 여름사과 출하 마무리…물량 줄면서 가격 회복세 - 구체적인 출하량·도매가격 변화를 담은 최상위 유통 후보를 누락했다.

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
