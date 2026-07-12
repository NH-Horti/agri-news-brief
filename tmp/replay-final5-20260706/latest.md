## Daily Eval (2026-07-06)
- Overall: **93.37** (pass)
- Operational: **94.51**
- Reader quality: **94.51** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **93.37** (needs_iteration, editorial_acceptance_gate_failed; editorial=83.5, operational=94.5)
- Scores: completeness=100.0, diversity=92.9, source=100.0, summary=91.0, freshness=90.0, retrieval=89.4, section_fit=95.8, core=100.0, commodity=99.8
- Briefing cards: 20 / Commodity cards: 28
- Sections: supply:5/5 raw=255, policy:5/5 raw=138, dist:5/5 raw=100, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.15, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=4.06, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=11, commodity_active_today=16, commodity_active_today_unlinked=5, commodity_coverage=0.33, commodity_strict_link=0.91, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.45, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.45** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 86.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, operational_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=85.0, section_fit=87.0, core=86.0, summary=77.0, missed=80.0, noise=84.0
- Summary: 전체 20개 카드와 섹션별 5개 구성은 충족했고, 수급·정책의 핵심 관측/물가/재해 대응 기사는 대체로 적절하다. 다만 유통 섹션에서 더 강한 산지경매·APC 운영 후보를 놓치고 지역 첫 출하·홍보성 카드가 들어갔으며, 정책에는 수급/시장성 양배추 기사가 섞였다. 병해충은 과수화상병 후보가 충분했는데 발생 규모와 재확산 위험을 담은 더 강한 기사를 핵심으로 쓰지 못했다. 여러 요약에 원문 파편과 어색한 문장이 남아 독자 효용을 떨어뜨린다.
- [moderate] missed_candidate: 햇마늘 경매 개시…“농가 제값받기 최선” - 유통 원자료 최상위권의 경매가·물량·운영 방식이 있는 구체적 산지경매 기사인데 빠졌다.
- [moderate] missed_candidate: 경북지역 조합공동사업법인, 농산물 판매확대로 농가소득 증대 앞장 - APC·조공법인·AI 선별·산지유통 경쟁력 등 섹션 핵심성이 높지만 누락됐다.
- [moderate] wrong_section: 생산비도 못 건지는 양배추 값...밭 갈아엎은 농민들 - 정부 대책 요구가 있지만 본문 핵심은 양배추 가격 폭락과 농가 피해로 수급/시장 기사에 가깝다.
- [moderate] missed_candidate: 농가 10곳 중 8곳 "유류비 21% 이상 상승… 2026년 하반기 자재 지원 필..." - 중동전쟁 이후 농자재 비용과 지원 필요를 다룬 정책성이 강한 후보가 양배추 시장 기사보다 적합했다.
- [moderate] missed_candidate: 폭염에 충북 과수화상병 소강 국면 - 51곳·21.68ha 피해와 소강 국면, 정밀예찰을 담아 과수화상병 상황 파악에 더 유용한 후보가 누락됐다.

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
