## Daily Eval (2026-08-11)
- Overall: **52.80** (fail)
- Operational: **95.95**
- Reader quality: **84.00** (capped; penalty=6.7, cap=84.0, reasons=pest_theme_duplicate, commodity_false_link, commodity_false_link_severe)
- Quality gate: **52.80** (needs_major_iteration, editorial_blocking_issue; editorial=52.8, operational=96.0)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=82.8, section_fit=100.0, core=88.3, commodity=85.2
- Briefing cards: 20 / Commodity cards: 28
- Sections: supply:5/5 raw=255, policy:5/5 raw=83, dist:5/5 raw=39, pest:5/5 raw=26
- Metrics: title_unique=1.00, domain_diversity=0.90, low_tier=0.20, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=3.80, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=9, commodity_active_today=14, commodity_active_today_unlinked=5, commodity_coverage=0.27, commodity_strict_link=0.89, commodity_false_link=0.11, commodity_pool_false_link=0.00, commodity_dominant_section=0.78, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **52.80** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 54.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=4, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=52.0, section_fit=57.0, core=43.0, summary=83.0, missed=40.0, noise=42.0
- Summary: 형식과 기사 수는 충족했지만 휴대전화 기사가 정책 핵심에 포함됐고, 유통은 동일 아이스크림 행사 중복과 홍보성 기사로 채워졌다. 원료곡 매입·출하비 지원·과수 탄저병 등 더 강한 후보를 놓쳐 편집 수용이 어렵다.
- [blocking] off_topic: "갤Z폴드8 256GB로 변경하면 지원금 추가" - 농업과 무관한 이동통신 단말기 재고 기사다.
- [major] duplicate_story: 농협대전공판장, '말복 맞이 아이스크림 나눔 이벤트' 진행 - 앞 카드와 동일한 공판장·수량·행사를 반복한다.
- [major] weak_core: 새벽 유통현장 에 아이스크림 1180개…폭염 식힌 농협대전공판장 - 단순 나눔 행사로 유통 운영 핵심성이 낮다. 코어에서 강등해야 한다.
- [major] missed_candidate: 과잉 보리 2만5000톤 특별 매입 - 정부·업계의 과잉물량 매입과 가격 방어는 가장 강한 정책 후보였다.
- [major] missed_candidate: “농가에 힘이 되겠습니다”…서울청과, 6개월간 2억4200만원 출하비 지원 - 포장·운송비 보전이라는 구체적 유통 지원이 행사성 카드보다 유용하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
