## Daily Eval (2026-09-09)
- Overall: **95.14** (pass)
- Operational: **98.04**
- Reader quality: **98.04** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **95.14** (needs_major_iteration, editorial_major_issue; editorial=75.4, operational=98.0)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=90.0, section_fit=100.0, core=85.0, commodity=97.7
- Briefing cards: 20 / Commodity cards: 56
- Sections: supply:5/5 raw=274, policy:5/5 raw=148, dist:5/5 raw=75, pest:5/5 raw=41
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.05, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.52, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=15, commodity_active_today=24, commodity_active_today_unlinked=9, commodity_coverage=0.45, commodity_strict_link=0.93, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.53, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **75.40** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 76.50; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=76.0, section_fit=78.0, core=68.0, summary=82.0, missed=72.0, noise=80.0
- Summary: 정원과 신선도는 좋지만 정책의 추석 물가 중복, 유통의 홍보성 핵심 선정, 병해충의 약한 사례성 꼬리가 품질을 낮춘다. 원시 후보에 더 강한 사과 수급·유통 운영 기사가 있어 교체 여지도 크다.
- [major] weak_core: 커피 1000잔으로 잇는 농협대전공판장 유통상생 약속 - 협약의 유통 내용보다 간식 제공을 앞세운 홍보성 기사로 핵심 카드에 약하다.
- [moderate] promotional_filler: 농협 괴산군지부·군자농협, 사과 공선장 찾아 출하 현장 점검 - 단순 방문·애로 청취에 그쳐 운영 변화나 실적 정보가 부족하다.
- [moderate] wrong_section: 이승돈 농진청장 "배 재배 85% '신고' 편중…녹색배 보급 확대" - 주된 내용이 품종 보급과 생산구조 개선이며 유통 운영 정보는 부차적이다.
- [moderate] duplicate_theme: 추석 앞두고 배값 작년보다 30% 넘게 가격 치솟았다 [프라이스&] - 한우·배 물가, 차례상 비용 기사와 추석 가격 주제가 반복되고 정부 설명자료와도 충돌한다.
- [moderate] bad_summary: [사실은 이렇습니다] 추석 대비 배 출하량 증가로 가격 은 안정 화되고 있... - 정정 대상 보도의 수치와 정부가 제시한 실제 출하량·가격 근거를 충분히 대비하지 않았다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
