## Daily Eval (2026-08-14)
- Overall: **80.03** (warn)
- Operational: **95.81**
- Reader quality: **86.37** (capped; penalty=9.4, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **80.03** (needs_major_iteration, editorial_major_issue; editorial=71.7, operational=95.8)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=82.5, section_fit=91.7, core=96.2, commodity=100.0
- Briefing cards: 20 / Commodity cards: 20
- Sections: supply:5/5 raw=310, policy:5/5 raw=100, dist:5/5 raw=55, pest:5/5 raw=22
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.20, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=3.71, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.8, commodity_weak=0.00, commodity_items=9, commodity_active_today=15, commodity_active_today_unlinked=6, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.44, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **71.65** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 72.60; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=72.0, section_fit=81.0, core=62.0, summary=79.0, missed=65.0, noise=75.0
- Summary: 수량과 신선도는 좋지만 정책 중복, 병해충 동일 기사 중복, 유통 핵심 선정의 약화가 뚜렷하다. 더 강한 운영·현장 피해 후보가 있는데 행사성·교육성 카드가 자리를 차지했다.
- [major] duplicate_story: 농진청, 참깨 수확 앞두고 병해충 적기 방제 당부 - 17번과 같은 농진청 발표를 재가공한 동일 기사다.
- [major] duplicate_theme: 구윤철 "청년 일자리 회복방안 조속히 발표…부진업종 맞춤형 고용대책... - 6번·9번과 동일한 정부 폭염 수급대책을 반복하며 제목도 농업 초점이 약하다.
- [moderate] weak_core: 농식품부·aT, 동남아 수출 설명회 열고 할랄·식품안전 규제 대응법 짚... - 일회성 설명회보다 양파 수급정책 전망이 농가 영향과 정책성이 크다. 코어에서 내려야 한다.
- [major] weak_core: 안전시설 미흡 논란… 89억 원대 영주 과수거점 APC 공사 현장 '주의' - 공사장 안전 논란은 유통 운영 영향이 제한적이어서 핵심 유통 기사로 약하다. 코어에서 내려야 한다.
- [moderate] weak_core: 철원군, 가락동 도매 현장 방문해 농가 소득향상 노력 - 지자체 방문 동정 성격이 강해 전국 독자용 핵심 기사로 부족하다. 코어에서 내려야 한다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
