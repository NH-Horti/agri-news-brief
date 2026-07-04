## Daily Eval (2026-07-01)
- Overall: **94.51** (pass)
- Operational: **95.61**
- Reader quality: **95.61** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **94.51** (needs_iteration, editorial_below_target_bounded_penalty; editorial=84.0, operational=95.6)
- Scores: completeness=100.0, diversity=95.0, summary=98.5, freshness=100.0, retrieval=72.4, section_fit=100.0, core=93.7, commodity=88.0
- Briefing cards: 20 / Commodity cards: 24
- Sections: supply:5/5 raw=203, policy:5/5 raw=111, dist:5/5 raw=52, pest:5/5 raw=12
- Metrics: title_unique=1.00, domain_diversity=0.65, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.92, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=5, commodity_active_today=14, commodity_active_today_unlinked=9, commodity_coverage=0.15, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.80, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=84.0, core=78.0, summary=82.0, missed=75.0, noise=79.0
- Summary: 분량은 4개 섹션 모두 5건으로 충족했고, 제주 월동채소 가격 급락, 정부 1조원 물가대책, 강서시장 영업공간 갈등, 고추 탄저병 등 핵심 소재는 일부 잘 잡았다. 그러나 공급·정책·유통에서 인물 선정, 지역 행사, 견학성 기사와 오염된 요약이 섞였고, 한농연 할당관세 비판, 마늘 수급안정 간담회, 화훼공판장 운영 한계, aT 유통본부 회의 같은 더 강한 후보를 놓쳤다. 발행 가능한 수준이지만 95점권의 선별 품질은 아니다.
- [major] wrong_section_or_weak_fit: 백성익 제주 감귤 연합회 회장, 수입농산물 관리 민간위원 선정 - 개인 위원 선정 중심의 정책성 인사 기사로 공급 동향성이 약하고 정책 10번과 같은 사안이다.
- [major] missed_stronger_candidate: 한농연 “농산물 가격 안정의 해법은 수입 아닌 ‘국내 생산 기반’에” - 정부 할당관세·수입 확대에 대한 농업계 반응으로 정책 핵심성이 높은데 누락됐다.
- [major] summary_quality: 재경차관, 수입란 유통업체 찾아 수급 점검…"가격안정 최선" - 요약에 ‘잠깐! 현재 Internet Explorer…’ 같은 크롤링 잡음이 포함됐다.
- [major] low_value_selection: 농산물 우수관리 인증 확대..."영농자재 80% 싸게 공급" - 요약이 깨져 있고 지방 GAP·자재 지원 성격이 강해 전국 정책 브리핑 가치가 낮다.
- [major] promotional_filler: 대신농협, 가락공판장 견학…간담회도 열어 - 견학·간담회 행사 중심으로 유통 운영 변화나 시장 영향이 약하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
