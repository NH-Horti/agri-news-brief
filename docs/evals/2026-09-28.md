## Daily Eval (2026-09-28)
- Overall: **88.65** (warn)
- Operational: **93.38**
- Reader quality: **89.96** (clear; penalty=3.4, cap=100.0, reasons=clear)
- Quality gate: **88.65** (needs_major_iteration, editorial_acceptance_gate_failed; editorial=76.8, operational=93.4)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=90.0, retrieval=90.0, section_fit=100.0, core=85.0, commodity=85.0
- Briefing cards: 20 / Commodity cards: 40
- Sections: supply:5/5 raw=347, policy:5/5 raw=204, dist:5/5 raw=65, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.20, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.44, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=1.9, commodity_weak=0.00, commodity_items=10, commodity_active_today=19, commodity_active_today_unlinked=9, commodity_coverage=0.30, commodity_strict_link=0.80, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.80, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **76.75** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 78.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=79.0, core=65.0, summary=92.0, missed=70.0, noise=76.0
- Summary: 분량과 요약은 안정적이지만, 공급·유통 간 배치 오류와 병해충 핵심기사 선정이 약하다. 특히 지역 안내성 기사를 핵심으로 올리고 더 구체적인 유통 운영 기사를 놓친 점이 품질을 낮춘다.
- [moderate] wrong_section: 가락시장 파렛트 출하 의무화 확대…느타리버섯·봄동·제주당근 대상 - 출하·하역·물류비 개선을 다룬 전형적인 유통 운영 기사다.
- [moderate] missed_candidate: 가락시장 파렛트 출하 의무화 확대…느타리버섯·봄동·제주당근 대상 - 구체적인 시행일과 대상 품목이 있는 물류 변화로 일부 현 선정기사보다 실무성이 높다.
- [moderate] weak_core: 옥천군농업기술센터, 포도 수확 후 "병해충 방제 ·충분한 물주기" 당부 - 지역 단위의 일반적 사후관리 안내여서 핵심기사로는 파급력이 부족하다.
- [moderate] weak_core: 함평군, '현장 밀착 상담'... 벼멸구 방제부터 폭염 안전까지 총력 - 6개월간 상담 실적을 소개하는 지자체 활동 홍보에 가깝고 현재 위험 신호가 약하다.
- [moderate] weak_core: 예산군, 농산물 가격 하락 농가에 가격 안정기금 지원 - 유용한 지역 지원 정보지만 전국 수급 영향이 제한돼 공급 핵심기사로는 약하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
