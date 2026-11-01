## Daily Eval (2026-10-08)
- Overall: **91.45** (warn)
- Operational: **96.64**
- Reader quality: **96.64** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **91.45** (needs_major_iteration, editorial_major_issue; editorial=76.2, operational=96.6)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=78.4, section_fit=100.0, core=93.6, commodity=76.2
- Briefing cards: 20 / Commodity cards: 28
- Sections: supply:5/5 raw=178, policy:5/5 raw=95, dist:5/5 raw=84, pest:5/5 raw=17
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.10, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=3.22, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=11, commodity_active_today=14, commodity_active_today_unlinked=3, commodity_coverage=0.33, commodity_strict_link=0.73, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.73, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **76.25** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 77.30; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=74.0, section_fit=88.0, core=69.0, summary=90.0, missed=67.0, noise=72.0
- Summary: 형식과 섹션 수는 충실하지만 공급 중복·해외 보충 기사, 약한 핵심 지정, 유통 공모성 기사 때문에 편집 품질이 낮아졌다. 원자료에 더 강한 수급 전망과 유통시설 후보가 있었다.
- [major] duplicate_story: 日 37일간 내린 비에 채솟값 인플레…"BOJ 정책에 영향 줄 수도" - 바로 앞 일본 양상추 급등 기사와 사실상 같은 사건이다.
- [major] missed_candidate: 내년 양파 공급 부족 우려…"재배면적 확대 필요" - 재배의향면적 7.6%·12% 감소를 제시한 직접적인 국내 공급 전망인데 누락됐다.
- [moderate] weak_core: 준고랭지 여름철 배추 생육 후기 작황 점검 - 구체적 작황 수치나 수급 전망이 없는 현장 방문성 기사다.
- [moderate] missed_candidate: 토마토·고추 오르고 호박·오이 내리고…과채값 '희비' - 품목별 10월 가격·재배면적 전망이 있어 해외 강우 기사보다 독자 효용이 높다.
- [moderate] promotional_filler: 2026년 농산물 마케팅대상 공모… 산지유통 혁신사례 발굴 - 모집 공고로서 실제 유통 운영이나 판로 변화 정보가 부족하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
