## Daily Eval (2026-09-04)
- Overall: **91.24** (pass)
- Operational: **95.80**
- Reader quality: **95.00** (capped; penalty=0.8, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **91.24** (needs_major_iteration, editorial_major_issue; editorial=77.0, operational=95.8)
- Scores: completeness=96.4, diversity=99.4, source=96.8, summary=100.0, freshness=100.0, retrieval=89.4, section_fit=91.2, core=99.3, commodity=93.8
- Briefing cards: 19 / Commodity cards: 41
- Sections: supply:5/5 raw=304, policy:5/5 raw=145, dist:5/5 raw=115, pest:4/5 raw=54
- Metrics: title_unique=1.00, domain_diversity=0.79, low_tier=0.16, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=3.19, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=8, commodity_active_today=11, commodity_active_today_unlinked=3, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.62, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **76.95** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 78.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, no_section_underfill)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=75.0, section_fit=76.0, core=74.0, summary=92.0, missed=68.0, noise=80.0
- Summary: 요약 품질과 공급 부문은 양호하지만, 유통 핵심기사 선정과 병해충 부문 편성이 약하다. 병해충에 무관한 R&D 예산과 간담회성 기사가 들어간 반면 직접적인 벼 병해충 후보를 놓쳤고, 정책·유통 간 K-푸드 수출 주제도 중복됐다.
- [major] wrong_section: 농촌분야 연구개발 예산 12.4% 증가 - 일반 농촌진흥청 R&D 예산 기사로 병해충·생육 위험과 직접 연결되지 않는다.
- [moderate] underfill: 병해충 섹션 4건 편성 - 원시 후보가 충분한데 목표 5건을 채우지 못했다.
- [major] missed_candidate: 진천군, 벼 병해충 확산 우려에 철저한 예찰·적기 방제 당부 - 도열병·이화명나방 등 구체적 위험과 최대 50% 감수 가능성을 담아 선택된 간담회보다 유용하다.
- [moderate] promotional_filler: 하학열 고성군수 농업인과 간담회 - 여러 지역 민원을 나열한 간담회 기사이며 병해충 정보는 일부 건의에 그친다.
- [moderate] weak_core: 원주시 농산물도매시장 추석 연휴 24~26일 휴장 - 단일 지역 휴장 공지는 핵심기사로 약하고 양구 APC 물류비 문제가 더 운영적이다.

### Improvement Hints
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
