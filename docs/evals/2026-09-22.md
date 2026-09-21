## Daily Eval (2026-09-22)
- Overall: **69.67** (fail)
- Operational: **88.51**
- Reader quality: **77.66** (capped; penalty=10.8, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **69.67** (needs_major_iteration, editorial_major_issue; editorial=65.0, operational=88.5)
- Scores: completeness=85.6, diversity=100.0, source=100.0, summary=98.1, freshness=100.0, retrieval=75.5, section_fit=100.0, core=97.9, commodity=90.0
- Briefing cards: 16 / Commodity cards: 26
- Sections: supply:5/5 raw=239, policy:5/5 raw=130, dist:5/5 raw=113, pest:1/5 raw=11
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.12, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.36, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.7, commodity_weak=0.00, commodity_items=7, commodity_active_today=12, commodity_active_today_unlinked=5, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.71, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **65.05** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 66.70; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, section_count_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 81.2 (underfilled)
- Components: article_selection=66.0, section_fit=74.0, core=57.0, summary=82.0, missed=45.0, noise=70.0
- Summary: 수급·유통은 기본 구성을 갖췄지만 핵심 기사 선택과 섹션 배치가 약하다. 특히 병해충은 활용 가능한 구체적 피해·방제 후보가 있는데도 1건만 실어 심각하게 미달했고, 그 1건도 저품질 일반 해설을 핵심으로 삼았다.
- [major] underfill: 병해충·생육위험 섹션 1건 편성 - 고유 후보가 여러 건인데 목표 5건, 최소 3건에도 못 미쳤다.
- [major] weak_core: 뙤약볕에 타들어 가는 농심...과일도 화상 입는다 '일소현상' - 저등급 매체의 일반 용어 해설로 당일 피해 규모나 대응 정보가 부족하다. 핵심에서 강등해야 한다.
- [major] missed_candidate: 박지원 "진도 대파 무름병, 농업재해로 인정" - 529농가·61㏊ 피해가 제시된 구체적 병해 사례로 일반 일소 해설보다 우선순위가 높다.
- [moderate] wrong_section: ‘애호박 1개 3,000원’ 추석 앞두고 채솟값 급등 - 정책 조치보다 소매가격 급등이 중심인 수급 기사다.
- [moderate] weak_core: [Issue+] AI가 바꾸는 수확후 관리, 데이터·장비 연결이 관건 - 수급 변동보다 장기 기술·저장유통 논의에 가깝고 당일 핵심성도 낮다. 핵심에서 강등해야 한다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-4). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
