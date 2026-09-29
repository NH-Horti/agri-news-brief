## Daily Eval (2026-09-30)
- Overall: **86.27** (warn)
- Operational: **94.19**
- Reader quality: **92.50** (capped; penalty=1.7, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **86.27** (needs_major_iteration, editorial_major_issue; editorial=72.1, operational=94.2)
- Scores: completeness=96.4, diversity=95.2, source=75.8, summary=100.0, freshness=100.0, retrieval=84.0, section_fit=98.3, core=88.9, commodity=85.0
- Briefing cards: 19 / Commodity cards: 24
- Sections: supply:5/5 raw=267, policy:5/5 raw=97, dist:5/5 raw=73, pest:4/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.89, low_tier=0.21, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=3.25, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=5, commodity_active_today=11, commodity_active_today_unlinked=6, commodity_coverage=0.15, commodity_strict_link=0.80, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.80, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **72.10** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 73.10; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=72.0, section_fit=80.0, core=64.0, summary=88.0, missed=62.0, noise=68.0
- Summary: 형식과 요약은 안정적이지만 핵심 기사 선정이 약하다. 정책·유통의 주요 전국 의제를 놓쳤고, 병해충은 기업 제품 홍보물을 코어로 올린 반면 배 열과 피해를 제외했다.
- [major] weak_core: 팜한농, 10월 농가 추천 제품 공개…나방 방제부터 저온기 수박·생분해... - 여러 제품을 소개하는 기업 홍보성 기사로 코어 가치가 낮다.
- [major] missed_candidate: “배 30~40%가 쩍쩍”…기후변화에 맥 못 추는 과원 - 피해 규모와 원인이 구체적인 현장 생산위험 기사인데 누락됐다.
- [moderate] underfill: 병해충 섹션 4건 편성 - 활용 가능한 후보가 있는데 목표 5건을 채우지 못했다.
- [moderate] wrong_section: 고창군, '수직확산형 순환팬' 보급…온실 고온 피해 줄인다 - 정책보다는 고온 생육피해 대응 기술로 pest 성격이 강하다.
- [major] missed_candidate: 李 "미래대응기금 활용 내년 명절 지원금 1조 확대" - 전국 단위 지원 규모와 재원 논란을 담은 핵심 정책 의제가 빠졌다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
