## Daily Eval (2026-07-01)
- Overall: **92.81** (pass)
- Operational: **94.11**
- Reader quality: **94.11** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **92.81** (needs_iteration, editorial_below_target_bounded_penalty; editorial=82.0, operational=94.1)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=75.5, section_fit=91.7, core=63.9, commodity=92.0
- Briefing cards: 20 / Commodity cards: 23
- Sections: supply:5/5 raw=204, policy:5/5 raw=111, dist:5/5 raw=52, pest:5/5 raw=12
- Metrics: title_unique=1.00, domain_diversity=0.70, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=4.14, false_positive=0.00, hard_reader_issues=0, weak_core=0.38, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=6, commodity_active_today=14, commodity_active_today_unlinked=8, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=78.0, section_fit=82.0, core=62.0, summary=85.0, missed=66.0, noise=72.0
- Summary: 건수와 신선도는 충족했지만, 정책과 유통 섹션에서 편집 판단이 크게 흔들렸다. 정책은 비농업성 벤처투자 기사를 core로 올리고 수입농산물 민관협의체를 중복 게재한 반면, 한농연의 수입 확대 비판·감자 계절관세 철폐 같은 더 중요한 농정 후보를 놓쳤다. 유통은 강서시장·마늘 간담회는 적절하나 직거래장 포토 중복과 지역 홍보성 카드가 강하고, 양파 공동선별·대만 수출 같은 실질 유통 기사를 누락했다. 병해충은 약한 원자료 풀을 감안해 일부 tail은 허용되지만, 고추 탄저병 같은 명명 병해 위험을 놓친 점이 아쉽다.
- [high] wrong_scope: 벤처투자 표준계약서 개정…RCPS 대신 CPS·사전동의권도 손질 - 농업·원예 정책성이 거의 없는 일반 벤처투자 기사인데 policy core로 배치됐다.
- [high] duplicate_story: 민·관이 수입농산물 관리에 머리를 맞대다…'수입농산물 관리 민관협의...' - 같은 민관협의체 출범 기사가 직전 카드와 중복돼 정책 슬롯을 낭비했다.
- [high] missed_stronger_candidate: 한농연 “농산물 가격 안정의 해법은 수입 아닌 ‘국내 생산 기반’에” - 정부 물가·수입 정책에 대한 농업계 핵심 반응으로, 선정된 약한 core보다 중요하다.
- [high] missed_stronger_candidate: 전주원예농협, 공동선별 물량 늘리고 수출도 ‘척척’ - 공동선별 확대, 대만 수출, 가격 지지까지 담긴 구체적 유통·수출 기사인데 누락됐다.
- [medium] duplicate_or_photo_filler: [포토] 도농상생 매장, 영암 농산물 직거래 판매 - 동서울-영암 직거래장 개점 기사와 같은 이야기의 포토성 반복이다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
