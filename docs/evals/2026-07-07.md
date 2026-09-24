## Daily Eval (2026-07-07)
- Overall: **93.68** (pass)
- Operational: **95.38**
- Reader quality: **94.63** (capped; penalty=0.8, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **93.68** (needs_iteration, editorial_acceptance_gate_failed; editorial=84.2, operational=95.4)
- Scores: completeness=96.4, diversity=99.4, source=96.8, summary=98.4, freshness=100.0, retrieval=87.5, section_fit=100.0, core=87.0, commodity=89.4
- Briefing cards: 19 / Commodity cards: 41
- Sections: supply:4/5 raw=250, policy:5/5 raw=109, dist:5/5 raw=84, pest:5/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.84, low_tier=0.16, summary_presence=1.00, summary_numeric=0.74, fresh_72h=1.00, fit_avg=4.65, false_positive=0.00, hard_reader_issues=0, weak_core=0.17, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=11, commodity_active_today=14, commodity_active_today_unlinked=3, commodity_coverage=0.33, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.73, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.20** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 86.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=86.0, section_fit=88.0, core=80.0, summary=84.0, missed=82.0, noise=86.0
- Summary: 전반적으로 수급·정책·유통·병해충의 핵심 흐름은 잡았지만, 원자료가 충분한데도 수급 섹션이 4건에 그친 점과 일부 섹션의 코어 지정이 약한 점이 감점 요인이다. 병해충 섹션은 과수화상병과 고추 병해를 포함해 방향은 좋으나, 오이 초기관리·예산군 종합 소식처럼 병해충성이 약한 꼬리 기사와 잡음 있는 요약이 섞였다. 정책·유통은 대체로 유효하나 더 강한 원자료 후보가 있었고 일부 요약 품질이 낮다.
- [moderate] underfill: 수급 섹션 4건 편성 - 원자료가 250건으로 충분한데 목표 5건을 채우지 못했다.
- [moderate] weak_core: "가격 폭락·농자재 폭등·CPTPP까지"···3중 악재에 농업계 거센 반발 - 정책 핵심 이슈는 맞지만 원자료에 더 높은 적합도의 같은 사안 기사(반값 농자재·농가소득 안전망)가 있었다.
- [moderate] bad_summary: 6월 경남 소비자물가 동향 …장바구니 물가 매섭게 올라 - 요약 첫 문장이 '6%)은'으로 시작해 문맥이 깨지고 핵심 수치 전달력이 낮다.
- [moderate] weak_core: "판로 걱정 덜겠다"... 고흥군 스마트 공급센터, 농산물 유통 거점 기대 - 구체적 유통 시설 기사라 섹션에는 맞지만 군수 현장점검 성격이 강해 코어로는 약하다.
- [moderate] noise: 예산군, 병해충 조기진단으로 농작물 피해 줄인다 - 요약에 산림계곡 단속·교량 정비까지 섞여 병해충 브리핑의 초점이 흐려진다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
