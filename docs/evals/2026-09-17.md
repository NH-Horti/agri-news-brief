## Daily Eval (2026-09-17)
- Overall: **81.05** (warn)
- Operational: **92.13**
- Reader quality: **88.73** (capped; penalty=3.4, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **81.05** (needs_major_iteration, editorial_major_issue; editorial=66.3, operational=92.1)
- Scores: completeness=92.8, diversity=94.2, source=71.1, summary=100.0, freshness=100.0, retrieval=78.5, section_fit=100.0, core=90.7, commodity=88.0
- Briefing cards: 18 / Commodity cards: 44
- Sections: supply:5/5 raw=237, policy:4/5 raw=113, dist:5/5 raw=57, pest:4/5 raw=19
- Metrics: title_unique=1.00, domain_diversity=0.89, low_tier=0.22, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=3.26, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.2, commodity_weak=0.00, commodity_items=8, commodity_active_today=15, commodity_active_today_unlinked=7, commodity_coverage=0.24, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.88, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **66.30** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 67.30; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 96.0 (soft_fallback)
- Components: article_selection=64.0, section_fit=65.0, core=68.0, summary=78.0, missed=61.0, noise=61.0
- Summary: 형식과 시의성은 양호하지만 감귤 기사 중복, 정책면의 추석 물가 편중, 유통면의 홍보성·주변부 기사 때문에 편집 품질이 크게 낮아졌다. 원자료에는 가락시장 물류대책과 수출 선적 등 더 강한 대체재가 있다.
- [major] duplicate_story: 제주감귤 상품 기준, 지난해와 동일...가공용수매단가 결정 - 2번 카드와 동일한 감귤위원회 결정 기사다.
- [major] duplicate_theme: 추석 차례상, 전통시장이 더 저렴해 - 정책면 3개 카드가 추석 차례상 물가에 집중되고 공급면 기사와도 겹친다.
- [moderate] wrong_section: 추석 차례상 비용 1년 새 4% 상승…전통시장이 대형마트보다 저렴 - 정책 조치보다 소비자가격 조사 중심의 공급·시장 동향 기사다.
- [moderate] weak_core: 추석 차례상 비용 1년 새 4% 상승…전통시장이 대형마트보다 저렴 - 반복적인 가격조사 기사여서 정책면 핵심성이 약하다. 코어에서 내려야 한다.
- [major] promotional_filler: 제주 감귤 농협 창립 66주년…지속 가능한 미래 다짐 - 창립 기념과 포괄적 다짐이 중심이라 당일 유통 변화나 운영 정보가 부족하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1), pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=11%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
