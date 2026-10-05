## Daily Eval (2026-10-06)
- Overall: **92.16** (warn)
- Operational: **96.12**
- Reader quality: **96.12** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **92.16** (needs_major_iteration, editorial_major_issue; editorial=76.2, operational=96.1)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=92.9, retrieval=90.6, section_fit=100.0, core=88.9, commodity=73.0
- Briefing cards: 20 / Commodity cards: 32
- Sections: supply:5/5 raw=336, policy:5/5 raw=190, dist:5/5 raw=75, pest:5/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.80, low_tier=0.15, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=2.70, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=7, commodity_active_today=16, commodity_active_today_unlinked=9, commodity_coverage=0.21, commodity_strict_link=0.71, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.86, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **76.15** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 77.10; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=76.0, section_fit=79.0, core=75.0, summary=82.0, missed=68.0, noise=78.0
- Summary: 정량 구성과 요약 형식은 안정적이지만, 공급 중복과 유통 핵심기사 누락이 크다. 특히 환율·운임의 수출 차질 기사 대신 가격동향·지역 판촉성 기사를 넣었고, 정책 7번은 제목과 요약이 맞지 않는다.
- [major] missed_candidate: 환율 급락에 수출 농가 ‘비상’…운임까지 크게 올라 ‘겹악재’ - 수출 채산성과 물류비를 함께 다룬 강한 운영 기사인데 지역 상담회와 일반 물가 기사에 밀렸다.
- [major] bad_summary: 원자재ㆍ환율 급등, 식품ㆍ외식 물가 압박…농식품부 "가격 인상 최소화" - 제목은 원자재·환율과 식품물가 대응인데 요약은 애호박 가격만 설명한다.
- [moderate] wrong_section: 9월 농산물 가격 전년 동월 대비 4% 하락…축산물은 3.7% 상승 - 유통 운영보다 거시 물가·수급 동향에 가까워 supply 또는 policy가 적합하다.
- [moderate] weak_core: 16명 농가 뭉친 '불정야뜨네'…복숭아로 올매출 35억 기록 - 유용한 지역 공동출하 사례지만 전국적 수출 차질 기사보다 핵심 우선순위가 낮다. 핵심에서 강등해야 한다.
- [moderate] duplicate_theme: 사과·배 가격 ‘뚝’ 떨어졌는데…“장보기 겁나” 곡소리 나오는 이유 - 채소 상승·과일 하락을 다룬 3번 기사와 내용이 크게 겹친다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
