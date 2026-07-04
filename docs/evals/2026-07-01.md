## Daily Eval (2026-07-01)
- Overall: **94.41** (pass)
- Operational: **95.61**
- Reader quality: **95.61** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **94.41** (needs_iteration, editorial_below_target_bounded_penalty; editorial=83.0, operational=95.6)
- Scores: completeness=100.0, diversity=95.0, summary=98.5, freshness=100.0, retrieval=72.4, section_fit=100.0, core=93.7, commodity=88.0
- Briefing cards: 20 / Commodity cards: 24
- Sections: supply:5/5 raw=203, policy:5/5 raw=111, dist:5/5 raw=52, pest:5/5 raw=12
- Metrics: title_unique=1.00, domain_diversity=0.65, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.92, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=5, commodity_active_today=14, commodity_active_today_unlinked=9, commodity_coverage=0.15, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.80, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.00** (target 95, needs_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=81.0, section_fit=84.0, core=78.0, summary=82.0, missed=74.0, noise=79.0
- Summary: 카드 수와 신선도는 충족했지만, 원자료에 더 강한 정책·유통 후보가 보이는데도 인물 선정, 견학, 지역 직거래장, 불완전한 YTN 요약 같은 약한 카드가 여러 장 들어갔다. 공급·병해충의 핵심 1~2건은 적절하나, 정책은 한농연 할당관세 비판을 놓쳤고 유통은 물류센터·APC·공판장 구조 이슈보다 행사성 카드 비중이 높다.
- [major] weak_selection: 농산물 우수관리 인증 확대..."영농자재 80% 싸게 공급" - 요약이 앵커·저작권 문구로 깨져 있고 지역 GAP 자재지원 성격이 강하다.
- [major] missed_opportunity: 한농연 “농산물 가격 안정의 해법은 수입 아닌 ‘국내 생산 기반’에” - 정부 물가대책·할당관세와 직접 맞물리는 전국 농업계 반응으로 정책 가치가 높다.
- [major] wrong_section: 백성익 제주 감귤 연합회 회장, 수입농산물 관리 민간위원 선정 - 생산·수급 기사라기보다 협의체 인사 동정이며 같은 이슈가 정책 카드에 이미 있다.
- [medium] promotional_filler: 대경사과원예농협, 자두 ·복숭아 본격 출하 - 초출하 행사 중심의 지역 단신으로 가격·수급 신호가 약하다.
- [medium] weak_core: 강서 시장 시경상생협의회, “ 시장 영업공간 분리 반대” - 도매시장 제도 갈등은 적합하지만 유통 섹션 유일 core로는 영향 범위가 좁다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
