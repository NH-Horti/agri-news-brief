## Daily Eval (2026-09-22)
- Overall: **80.56** (warn)
- Operational: **93.03**
- Reader quality: **87.29** (capped; penalty=5.7, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **80.56** (needs_major_iteration, editorial_major_issue; editorial=70.1, operational=93.0)
- Scores: completeness=96.4, diversity=100.0, source=100.0, summary=98.4, freshness=100.0, retrieval=75.5, section_fit=100.0, core=98.9, commodity=90.0
- Briefing cards: 19 / Commodity cards: 27
- Sections: supply:5/5 raw=238, policy:5/5 raw=130, dist:5/5 raw=113, pest:4/5 raw=11
- Metrics: title_unique=1.00, domain_diversity=0.79, low_tier=0.11, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=4.14, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.4, commodity_weak=0.00, commodity_items=7, commodity_active_today=12, commodity_active_today_unlinked=5, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.71, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **70.10** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 72.30; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=73.0, section_fit=70.0, core=62.0, summary=77.0, missed=68.0, noise=72.0
- Summary: 수량은 대체로 충족했지만 약한 코어, 가격 기사의 정책 섹션 배치, 지역 현장점검성 filler가 품질을 낮췄다. 특히 pest는 구체적인 레드향 열과 피해를 놓치고 일반 해설을 코어로 삼았다.
- [major] weak_core: [Issue+] AI가 바꾸는 수확후 관리, 데이터·장비 연결이 관건 - 당일 수급 신호보다 중장기 기술 기획에 가까워 supply 코어로 약하다.
- [moderate] wrong_section: ‘애호박 1개 3,000원’ 추석 앞두고 채솟값 급등 - 정책 조치보다 소매가격 급등이 중심인 수급 기사다.
- [major] weak_core: 뙤약볕에 타들어 가는 농심...과일도 화상 입는다 '일소현상' [지식용어...] - 저품질 출처의 일반 용어 해설로 당일 피해 대응 코어가 되기 어렵다.
- [major] missed_candidate: 레드향 열과 피해 벌써 20%…올해도 되풀이 - 피해율과 품목이 명확한 KBS 현장 기사로 일반 일소 해설보다 강하다.
- [moderate] promotional_filler: 충북농협, 추석 명절 맞이 괴산 사과 선별·출하 상황 점검 및 농가 애로... - 기관 방문·격려 중심이며 유통 운영 변화나 물량 성과가 부족하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
