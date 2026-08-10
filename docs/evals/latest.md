## Daily Eval (2026-08-11)
- Overall: **61.10** (fail)
- Operational: **97.10**
- Reader quality: **84.00** (capped; penalty=6.7, cap=84.0, reasons=pest_theme_duplicate, commodity_false_link, commodity_false_link_severe)
- Quality gate: **61.10** (needs_major_iteration, editorial_blocking_issue; editorial=61.1, operational=97.1)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=83.5, section_fit=100.0, core=93.7, commodity=85.2
- Briefing cards: 20 / Commodity cards: 28
- Sections: supply:5/5 raw=255, policy:5/5 raw=84, dist:5/5 raw=39, pest:5/5 raw=27
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.15, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=3.80, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=9, commodity_active_today=14, commodity_active_today_unlinked=5, commodity_coverage=0.27, commodity_strict_link=0.89, commodity_false_link=0.11, commodity_pool_false_link=0.00, commodity_dominant_section=0.78, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **61.10** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 64.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=4, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=62.0, section_fit=66.0, core=50.0, summary=85.0, missed=55.0, noise=47.0
- Summary: 수량과 요약 형식은 좋지만, 정책의 스마트폰 오탐과 유통의 동일 이벤트 중복이 치명적이다. 강한 보리 수급대책·출하비 지원 기사를 놓치고 홍보성 소재를 핵심으로 올려 편집 품질이 크게 낮아졌다.
- [blocking] off_topic: "갤Z폴드8 256GB로 변경하면 지원금 추가" - 농업·농촌 정책과 무관한 이동통신 재고 기사다.
- [major] duplicate_story: 농협대전공판장, '말복 맞이 아이스크림 나눔 이벤트' 진행 - 앞 카드와 아이스크림 1180개 전달이라는 동일 사건이다.
- [major] weak_core: 새벽 유통현장 에 아이스크림 1180개…폭염 식힌 농협대전공판장 - 일회성 격려 이벤트로 핵심 유통 뉴스가 아니다. core에서 demote해야 한다.
- [major] missed_candidate: “농가에 힘이 되겠습니다”…서울청과, 6개월간 2억4200만원 출하비 지원 - 운송·포장비 보전이라는 구체적 유통 지원책이 이벤트 기사보다 훨씬 강하다.
- [major] missed_candidate: 과잉 보리 2만5000톤 특별 매입 - 정부와 업계의 과잉물량 매입은 전국 수급·가격 정책의 핵심 현안이다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
