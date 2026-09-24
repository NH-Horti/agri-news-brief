## Daily Eval (2026-07-09)
- Overall: **86.62** (pass)
- Operational: **92.48**
- Reader quality: **90.23** (capped; penalty=2.2, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **86.62** (needs_iteration, editorial_major_issue; editorial=83.5, operational=92.5)
- Scores: completeness=89.2, diversity=93.2, source=65.9, summary=100.0, freshness=100.0, retrieval=90.0, section_fit=100.0, core=92.3, commodity=96.1
- Briefing cards: 17 / Commodity cards: 12
- Sections: supply:4/5 raw=180, policy:5/5 raw=138, dist:5/5 raw=59, pest:3/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.71, low_tier=0.24, summary_presence=1.00, summary_numeric=0.88, fresh_72h=1.00, fit_avg=4.14, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=7, commodity_active_today=10, commodity_active_today_unlinked=3, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.55** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 83.60; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, no_section_underfill)
- Section count gate: 95.5 (soft_fallback)
- Components: article_selection=84.0, section_fit=87.0, core=82.0, summary=92.0, missed=72.0, noise=85.0
- Summary: 전반적으로 선택 기사들은 대부분 농업 브리핑 범위 안에 있고 요약도 읽기 쉽다. 다만 원자료가 충분한데도 supply는 4건, pest는 3건에 그쳐 일일 브리핑 완성도가 떨어졌다. 특히 과일류 농업관측, 민생안정지원단 먹거리 물가 점검, 취약계층 농식품 물가 분석, 장마철 병해충·복합해충 기사 등 더 강한 후보가 보이는 상황에서 일부 지역 토론회·행사성 기사와 중복 가격폭락 테마가 남았다.
- [major] underfill: pest 섹션 3건 편성 - 원자료 33건인데 최소 fallback 3건에 머물렀고 장마철 병해충·복합해충 후보가 남아 있다.
- [moderate] underfill: supply 섹션 4건 편성 - 원자료 180건으로 5건 편성이 가능했는데 한 칸이 비었다.
- [moderate] missed_candidate: 7월 과일류 농업관측 - 사과·배·복숭아 생산·출하 전망을 담은 강한 수급 후보가 빠졌다.
- [major] missed_candidate: 민생안정지원단, 계란·축산물 등 먹거리 물가 현장점검 - 범정부 물가 현장점검으로 정책 핵심성이 높은데 지역 청년 스마트팜 토론회보다 뒤로 밀렸다.
- [moderate] missed_candidate: "취약계층, 농식품 물가 상승 직격탄 맞아" - KREI 기반 물가 정책 분석으로 독자 유용성이 높지만 누락됐다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1), pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
