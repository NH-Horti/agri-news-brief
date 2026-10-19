## Daily Eval (2026-10-20)
- Overall: **64.46** (fail)
- Operational: **84.39**
- Reader quality: **70.21** (capped; penalty=14.2, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **64.46** (needs_major_iteration, editorial_major_issue; editorial=64.0, operational=84.4)
- Scores: completeness=82.2, diversity=93.8, source=100.0, summary=100.0, freshness=100.0, retrieval=76.2, section_fit=100.0, core=86.7, commodity=97.5
- Briefing cards: 17 / Commodity cards: 61
- Sections: supply:5/5 raw=275, policy:4/5 raw=56, dist:5/5 raw=109, pest:3/5 raw=13
- Metrics: title_unique=1.00, domain_diversity=0.88, low_tier=0.12, summary_presence=1.00, summary_numeric=0.76, fresh_72h=1.00, fit_avg=3.64, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=5.4, commodity_weak=0.00, commodity_items=13, commodity_active_today=18, commodity_active_today_unlinked=5, commodity_coverage=0.39, commodity_strict_link=0.92, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.54, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **64.00** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 64.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, no_section_underfill)
- Section count gate: 95.5 (soft_fallback)
- Components: article_selection=64.0, section_fit=64.0, core=55.0, summary=86.0, missed=58.0, noise=58.0
- Summary: 가격·수급 핵심은 잡았지만 홍보성·행사성 꼬리가 많고, pest의 핵심 병해충 기사를 놓쳤다. 일부 작은 지역 수출과 가짜뉴스 대응을 core로 둔 판단도 약하다.
- [major] missed_candidate: 농진청, 탄저병 균 61종 재정리…종별 약효는 숙제 - 선정된 재배교육·스마트과수원보다 명확한 병해충 위험 정보다.
- [moderate] wrong_section: 울릉군, 현장 실증교육 통해 대체작물 재배기술 보급 - 일반 대체작물 교육으로 생육 위험이나 방제 신호가 약하다.
- [moderate] weak_core: 김해 '진영단감' 미국 괌 수출길 올라 - 3.6t 규모의 지역 선적식으로 전국적 유통 중요도가 제한적이다.
- [moderate] promotional_filler: 대아청과, 가락시장서 '가족 김장' 웃음꽃 '활짝' - 가족 체험행사로 유통 운영 정보가 거의 없다.
- [moderate] weak_core: 농식품부, 소셜미디어 가짜뉴스 엄정 대응…악의적 게시 법적 조치 - 농업 생산·시장에 미치는 직접성이 낮아 일일 정책 core로 약하다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 동일 이슈가 브리핑/품목 보드에 반복 노출됩니다. story signature 중복 억제와 commodity surface 재사용 상한이 필요합니다.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1), pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=12%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
