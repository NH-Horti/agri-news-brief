## Daily Eval (2026-07-24)
- Overall: **80.18** (warn)
- Operational: **90.43**
- Reader quality: **88.18** (capped; penalty=2.2, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **80.18** (needs_major_iteration, editorial_major_issue; editorial=66.8, operational=90.4)
- Scores: completeness=89.2, diversity=93.2, source=65.9, summary=96.5, freshness=100.0, retrieval=89.4, section_fit=96.4, core=85.2, commodity=100.0
- Briefing cards: 17 / Commodity cards: 15
- Sections: supply:4/5 raw=205, policy:4/5 raw=128, dist:5/5 raw=52, pest:4/5 raw=31
- Metrics: title_unique=1.00, domain_diversity=0.94, low_tier=0.24, summary_presence=1.00, summary_numeric=0.65, fresh_72h=1.00, fit_avg=4.02, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=6, commodity_active_today=11, commodity_active_today_unlinked=5, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.33, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **66.85** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 70.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, section_count_score_min, no_section_underfill)
- Section count gate: 94.0 (soft_fallback)
- Components: article_selection=70.0, section_fit=76.0, core=66.0, summary=70.0, missed=55.0, noise=60.0
- Summary: 형식상 전 섹션을 채웠지만, 충분한 후보가 있는데도 supply·policy·pest가 4건에 그쳤고 같은 강원 농산물 가격안정 사업이 3개 카드로 반복됐다. 수박 가격 하락도 중복 테마로 뽑혀 핵심 슬롯을 소모했으며, 정책·수급의 더 강한 전국성 후보를 놓쳤다. dist는 비교적 양호하나 일부 지역·프로필성 꼬리가 약하고, pest는 실제 발생·위험 기사보다 기술자료성 카드가 코어로 올라간 점이 아쉽다. 일부 요약에는 포털/AI 문구가 섞여 독자용 품질이 떨어진다.
- [major] duplicate_story: 강원농협, 도청과 함께 지역 농산물 가격안정 총력 / 강원도·강원농협 도내 농산물 가격·수급 안정사업 추진 / 강원도·강원농협, 도내 농산물 가격안정에 총력 - 동일한 강원도·강원농협 가격안정 사업을 3개 카드로 반복해 지면을 크게 낭비했다.
- [moderate] duplicate_theme: 수박값 1년 새 36%↓ / 이제 좀 사먹겠네…작년보다 확 싸진 국민 과일 - 두 카드가 같은 aT 수박 가격 하락 수치를 중심으로 거의 같은 내용을 전달한다.
- [major] missed_candidate: 농산물 값 널뛰는데 정부 관리 물량은 10% 그쳐 - 개정 농안법·가격안정제와 정부 수급관리 한계를 다룬 최상위 전국 정책 후보를 누락했다.
- [major] missed_candidate: 폭우·폭염 반복 ‘도깨비 장마’…농산물값 바닥 장기화 - 가격 약세 장기화와 출하조절 난항을 종합한 강한 수급 기사인데 중복 수박·지역사업보다 뒤로 밀렸다.
- [moderate] weak_core: 배나무 재배 기술 병해충 방제 검은별무늬병 - 시의성 있는 뉴스라기보다 재배기술 자료에 가까운데 pest 코어로 선정됐다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1), policy(-1), pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
