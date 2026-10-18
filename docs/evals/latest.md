## Daily Eval (2026-10-19)
- Overall: **92.02** (warn)
- Operational: **96.78**
- Reader quality: **96.78** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **92.02** (needs_major_iteration, editorial_major_issue; editorial=68.0, operational=96.8)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=91.4, retrieval=87.2, section_fit=92.4, core=99.6, commodity=99.0
- Briefing cards: 20 / Commodity cards: 72
- Sections: supply:5/5 raw=428, policy:5/5 raw=142, dist:5/5 raw=112, pest:5/5 raw=26
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.15, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.80, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=8, commodity_active_today=15, commodity_active_today_unlinked=7, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **67.95** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 69.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=67.0, section_fit=80.0, core=55.0, summary=86.0, missed=62.0, noise=60.0
- Summary: 수량과 형식은 충족했지만 핵심기사 선정이 약하다. 단감 중복, 의성 경품행사의 유통 핵심 지정, 지역 파쇄사업의 정책 핵심 지정이 편집 가치를 크게 낮췄으며 더 강한 시세·수출 후보를 놓쳤다.
- [moderate] duplicate_theme: 단감인데 가격은 안 달다…가을 과일 중 유독 가격 뛴 단감, 왜 - 1번 기사와 같은 단감 작황 부진·가격 상승을 반복하며 두 기사 모두 핵심이다.
- [moderate] missed_candidate: [한눈에 보는 시세] 상추, 물량 늘고 소비 침체 여파 ‘약세늪’ - 전년 대비 83% 하락이라는 강한 시장 신호가 단감 중복보다 중요하다.
- [moderate] weak_core: "영농부산물 파쇄해드려요" 청주시, 19일부터 신청접수 - 단일 지자체 신청 안내로 전국 정책 핵심기사 가치가 낮다. 핵심에서 강등해야 한다.
- [major] weak_core: 의성군 농산물 공판장, 출하농가·중매인· 유통 종사자·소비자를 격려하는... - 경품 제공 격려행사는 유통 운영 변화가 없는 행사성 기사다. 핵심에서 강등해야 한다.
- [moderate] missed_candidate: 동읍농협, 폭염·가뭄 뚫고 베트남 수출 길…단감 9.3톤 선적 - 실제 선적량·공동선별·운송 방식이 담긴 운영형 수출 기사로 행사 기사보다 강하다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
