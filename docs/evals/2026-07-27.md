## Daily Eval (2026-07-27)
- Overall: **94.09** (pass)
- Operational: **94.89**
- Reader quality: **94.89** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **94.09** (needs_iteration, editorial_acceptance_gate_failed; editorial=84.8, operational=94.9)
- Scores: completeness=100.0, diversity=96.4, source=100.0, summary=91.0, freshness=90.0, retrieval=91.9, section_fit=97.2, core=92.2, commodity=98.1
- Briefing cards: 20 / Commodity cards: 20
- Sections: supply:5/5 raw=247, policy:5/5 raw=151, dist:5/5 raw=49, pest:5/5 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.65, low_tier=0.15, summary_presence=1.00, summary_numeric=0.55, fresh_72h=1.00, fit_avg=4.19, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=6, commodity_active_today=10, commodity_active_today_unlinked=4, commodity_coverage=0.18, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.80** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 85.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, operational_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=86.0, section_fit=90.0, core=91.0, summary=74.0, missed=80.0, noise=85.0
- Summary: 섹션별 5건을 채우고 핵심 기사도 대체로 강하지만, 일부 비핵심 카드가 더 직접적인 농업·병해충 후보를 밀어냈다. 특히 정책의 범용 물가 법제 기사와 병해충의 일반 재배관리 공지는 선별력이 약하다. 기사 선택보다 더 큰 약점은 요약으로, 핵심 수치·피해 범위·정책 내용 대신 인용문이나 본문 조각을 붙인 카드가 여러 건 있어 실무 활용성이 떨어진다.
- [moderate] missed_candidate: 정부, 압수물품 선제 매각 허용…물가안정법 개정 추진 - 범용 물가·매점매석 법제 기사로 농업 직접성이 낮다. 농산물 수급관리 제도 개편 후보가 더 적합하다.
- [moderate] missed_candidate: 사천시, 콩 개화기 물관리·병해충 적기 대응 당부 - 병해충명이 불분명한 일반 재배관리 공지다. 복숭아명나방 700㏊ 방제처럼 구체적인 후보가 보인다.
- [minor] duplicate_theme: "무 한 박스 4000원" 농산물 값 폭락에 고랭지 농가 비명 - 첫 카드의 생산비 급등·출하가 폭락 문제와 주제가 겹쳐 공급 섹션의 정보 폭이 좁아진다.
- [moderate] bad_summary: 결주에 흉작까지…강원 감자 농가의 눈물 - 요약이 과거 현장 사진 설명에 머물러 보급종 ‘두백’ 품질 논란과 공급량 76%라는 핵심을 누락했다.
- [moderate] bad_summary: "무 한 박스 4000원" 농산물 값 폭락에 고랭지 농가 비명 - 농민 발언 조각만 있어 가격 하락 폭, 폐기 규모, 원인과 대응을 파악할 수 없다.

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
