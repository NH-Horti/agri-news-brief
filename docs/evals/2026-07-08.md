## Daily Eval (2026-07-08)
- Overall: **84.18** (warn)
- Operational: **95.79**
- Reader quality: **90.12** (clear; penalty=5.7, cap=100.0, reasons=clear)
- Quality gate: **84.18** (needs_major_iteration, editorial_major_issue; editorial=79.2, operational=95.8)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=89.4, section_fit=98.6, core=100.0, commodity=99.1
- Briefing cards: 20 / Commodity cards: 20
- Sections: supply:5/5 raw=195, policy:5/5 raw=143, dist:5/5 raw=90, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.80, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.08, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=3.1, commodity_weak=0.00, commodity_items=10, commodity_active_today=12, commodity_active_today_unlinked=2, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **79.25** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 82.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=78.0, section_fit=79.0, core=80.0, summary=90.0, missed=72.0, noise=76.0
- Summary: 분량과 신선도, 요약 품질은 양호하지만 가격안정제·농협 강서공판장 점검 기사가 여러 섹션에 반복 배치되며 핵심 의제 다양성이 떨어졌다. 정책·유통 섹션에서 더 강한 후보가 보였는데도 동정성·홍보성·타 섹션성 카드가 들어갔고, 병해충도 제품 제안성 카드가 한 자리를 차지했다.
- [major] duplicate_story: [동정] 강호동 농협중앙회장, 여름철 기상재해 대비 농산물 수급 점검 / 강호동 농협중앙회장 "농산물 수급 안정 만전" - 동일한 강서공판장 수급 점검 내용을 공급과 정책에 중복 게재했다.
- [major] duplicate_theme: 농산물 가격안정제 관련 3건 - 가격안정제·농가부담 완화 대책이 공급, 정책, 유통에 반복되어 섹션별 차별성이 약하다.
- [major] missed_candidate: 취약계층에 더 비싼 장바구니…"맞춤형 물가정책 필요" - 정책 원풀 최상위의 KREI 연구 기사로 정책성이 강한데 누락됐다.
- [moderate] weak_core: 농협, 수급 관리·AI 자산관리·푸드테크 지원 확대…하반기 사업 본격... - 농산물 정책보다 농협 금융·AI 자산관리까지 섞인 잡다한 기관 동정성 기사다.
- [moderate] wrong_section: 농산물 값↓·농자재값↑…정부, 농가 경영부담 완화에 총력 - 유통·물류 기사라기보다 정부 경영부담 완화 정책 기사다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=5%, promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
