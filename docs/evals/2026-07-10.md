## Daily Eval (2026-07-10)
- Overall: **96.69** (pass)
- Operational: **97.78**
- Reader quality: **97.24** (clear; penalty=0.5, cap=100.0, reasons=clear)
- Quality gate: **96.69** (needs_minor_iteration, editorial_acceptance_gate_failed; editorial=85.8, operational=97.8)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=98.5, freshness=100.0, retrieval=86.9, section_fit=97.2, core=99.5, commodity=94.9
- Briefing cards: 20 / Commodity cards: 54
- Sections: supply:5/5 raw=188, policy:5/5 raw=141, dist:5/5 raw=84, pest:5/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.10, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=3.55, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.3, commodity_weak=0.00, commodity_items=5, commodity_active_today=15, commodity_active_today_unlinked=10, commodity_coverage=0.15, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.60, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **85.80** (daily target 88, tier=needs_iteration, needs_minor_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 86.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=87.0, section_fit=88.0, core=85.0, summary=84.0, missed=85.0, noise=85.0
- Summary: 전체 20건을 채운 점과 양파 수급, 장마 후 채소 가격, 도매시장 TF, 온라인도매시장 물류, 주요 병해충 경보 등 핵심 축은 잘 잡았다. 다만 공급·유통 꼬리기사에 해외 기술 소개나 지역 홍보성 협약/공급 안내가 섞였고, 유통 섹션에서는 더 구체적인 APC·공동선별·물류 후보를 일부 놓쳤다. 몇몇 농민신문 요약은 제목 반복·본문 절단 흔적이 있어 독자 효용을 떨어뜨린다.
- [moderate] weak_core: 대관령원협, 산지공판장 초매식 개최 - 산지 출하 개시로 유통 관련성은 있지만 초매식 중심의 지역 행사성 기사라 핵심 유통 카드로는 약하다.
- [moderate] wrong_section: 충북 포도, 수출 현장 이상 無 ··· 품질․안전 모두 잡았다 - 수출 품질·검역·판로 성격이 강해 공급보다 유통/수출 섹션에 더 적합하다.
- [moderate] noise: “수입 70%는 데이터 팔아 얻죠”…중국 ‘AI 상추재배기지’ 무슨 일? - 해외 스마트팜 소개성 기사로 당일 국내 수급 브리핑의 실무성은 낮다.
- [moderate] promotional_filler: 청양군농업기술센터, 가을 배추 우량묘 110만 본 공급 - 군 단위 신청 안내 성격이 강해 전국 독자에게 주는 수급 정보 가치가 제한적이다.
- [moderate] promotional_filler: 합천군, 사과 대추 유통 경쟁력 강화 - 지역 공선출하 협약 홍보에 가깝고 구체적 물류·시장 운영 변화가 약하다.

### Improvement Hints
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=15%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
