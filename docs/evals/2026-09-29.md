## Daily Eval (2026-09-29)
- Overall: **75.71** (warn)
- Operational: **88.70**
- Reader quality: **80.90** (capped; penalty=7.8, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **75.71** (needs_major_iteration, editorial_major_issue; editorial=71.2, operational=88.7)
- Scores: completeness=85.6, diversity=92.0, source=60.0, summary=100.0, freshness=100.0, retrieval=84.8, section_fit=100.0, core=83.3, commodity=88.0
- Briefing cards: 16 / Commodity cards: 24
- Sections: supply:5/5 raw=163, policy:3/5 raw=63, dist:5/5 raw=66, pest:3/5 raw=27
- Metrics: title_unique=1.00, domain_diversity=0.94, low_tier=0.25, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=3.57, false_positive=0.00, hard_reader_issues=0, weak_core=0.11, editorial_penalty=1.0, commodity_weak=0.00, commodity_items=8, commodity_active_today=12, commodity_active_today_unlinked=4, commodity_coverage=0.24, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.88, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **71.25** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 73.10; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 95.0 (minimum_fallback)
- Components: article_selection=71.0, section_fit=73.0, core=66.0, summary=84.0, missed=61.0, noise=76.0
- Summary: 유통 섹션은 견조하지만 정책 섹션의 핵심 선별과 충원이 크게 부족하다. 공급에도 해외 기술지원 등 약한 꼬리 기사가 섞였고, 병해충은 후보 풀이 약하더라도 핵심성이 낮다.
- [major] underfill: 정책 섹션 3건 편성 - 원시 후보가 충분한데 목표 5건보다 두 건 부족하다.
- [major] missed_candidate: '3중고' K-농업…소득·기술·CPTPP 모두 '위기' - 소득·기술·통상을 아우르는 전국 단위 정책 현안이 지역 건의 기사보다 중요하다.
- [moderate] weak_core: 문경시, 이철우 경북도지사와 정책소통...국·도비 지원 건의 - 확정 정책이 아닌 지역 예산 건의라 핵심성이 약하다.
- [moderate] missed_candidate: 임동규 김천시의원, 농축산물가격안정기금 고령농 은퇴 지원 등 적극 활용 촉구 - 10년간 미집행된 가격안정기금 문제는 단일 농가 실증보다 정책적 실효성이 높다.
- [moderate] wrong_section: [여기는 안동] 경북도·일본 나라현, 안동서 문화예술 교류 외 - 농가 한 곳의 비료 투입 실증은 정책보다 생산기술 기사에 가깝다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: policy, pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-2), pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
