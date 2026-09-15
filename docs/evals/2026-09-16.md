## Daily Eval (2026-09-16)
- Overall: **78.37** (warn)
- Operational: **92.72**
- Reader quality: **83.77** (capped; penalty=8.9, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **78.37** (needs_major_iteration, editorial_major_issue; editorial=75.4, operational=92.7)
- Scores: completeness=100.0, diversity=88.9, source=80.0, summary=100.0, freshness=100.0, retrieval=87.9, section_fit=91.7, core=92.1, commodity=100.0
- Briefing cards: 20 / Commodity cards: 35
- Sections: supply:5/5 raw=267, policy:5/5 raw=130, dist:5/5 raw=91, pest:5/5 raw=27
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.20, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=4.02, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=2.8, commodity_weak=0.00, commodity_items=7, commodity_active_today=17, commodity_active_today_unlinked=10, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **75.40** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 76.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=73.0, section_fit=80.0, core=72.0, summary=91.0, missed=68.0, noise=69.0
- Summary: 분량과 요약은 안정적이지만 공급·유통 섹션에 인물 소개와 견학성 기사가 섞였고, 파렛트 물류 기사가 중복됐다. 정책·유통의 강한 후보를 두고 지역 행사성 카드가 채택돼 핵심 선별도 개선이 필요하다.
- [moderate] wrong_section: 마늘·양파 생산자단체 "새 농안법, 실질적 가격 안전망 돼야" - 개정 농안법과 가격안정제 제도 요구가 중심인 정책 기사다.
- [major] promotional_filler: 박노봉(익산원예농협 멜론 공선회장) - 농사경력 40년 베테랑, 배움엔 끝... - 개별 농가 인물 소개로 당일 수급 판단에 기여하지 않는다.
- [major] duplicate_story: 봄동·당근 파렛트 출하 의무화 - dist의 가락시장 파렛트 물류 기사와 같은 정책·품목·시행 내용을 다룬다.
- [moderate] missed_candidate: 모처럼 농축산물 가격 안정...추석 차례상 비용도 '뚝' - 전국 품목별 가격 수치를 제공해 지역 자재지원·회의 기사보다 정책 효과 판단에 유용하다.
- [major] promotional_filler: 영등포농협, 일본 동경농업대 방문단에 우리 농산물 유통 현장 소개 - 방문단 견학이 중심이며 유통 변화나 사업 성과가 없다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
