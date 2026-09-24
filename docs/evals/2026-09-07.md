## Daily Eval (2026-09-07)
- Overall: **92.68** (pass)
- Operational: **96.51**
- Reader quality: **94.89** (clear; penalty=1.6, cap=100.0, reasons=clear)
- Quality gate: **92.68** (needs_major_iteration, editorial_major_issue; editorial=78.2, operational=96.5)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=94.3, retrieval=91.2, section_fit=97.2, core=92.6, commodity=95.3
- Briefing cards: 20 / Commodity cards: 54
- Sections: supply:5/5 raw=331, policy:5/5 raw=159, dist:5/5 raw=120, pest:5/5 raw=42
- Metrics: title_unique=1.00, domain_diversity=0.80, low_tier=0.15, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=3.13, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.9, commodity_weak=0.00, commodity_items=11, commodity_active_today=22, commodity_active_today_unlinked=11, commodity_coverage=0.33, commodity_strict_link=0.82, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.55, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **78.15** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 78.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=76.0, section_fit=82.0, core=81.0, summary=91.0, missed=70.0, noise=65.0
- Summary: 수량과 요약은 안정적이지만 정책 섹션의 CPTPP 중복과 비농업성 주간 일정, 지역 지원성 기사가 품질을 낮춘다. 공급도 전국 수급 후보보다 현장 점검·지역 작황 기사를 우선했다.
- [major] duplicate_story: 노만호 한종협 대표 "검역이 막던 수입품 들어오면 농업 생산기반 무너... - 같은 매체·인물·CPTPP 검역 우려를 다룬 7번 카드와 사실상 같은 이야기다.
- [moderate] noise: [이번주 경제] 8월 고용 성적표 나온다…추석 물가 대응도 본격화 - 기사 중심이 고용·경기 일정이며 농업 정책 정보는 부차적이다.
- [moderate] promotional_filler: 완주 구이농협, 배추 모종 무상지원 공급 - 단일 농협의 소규모 조합원 지원으로 정책 파급력과 전국성이 낮다.
- [moderate] missed_candidate: 가을 감자 재배의향면적 전년보다 4% 증가 - 전년·평년 대비 면적 변화가 명확한 전국 수급 관측인데 지역 현장 점검 기사보다 우선되지 않았다.
- [moderate] weak_core: 고령딸기 수출 3년 새 36배 성장…민관 협업 전국서 통했다 - 구체적인 수출 성장과 판로 확대 성과로 현재 비핵심 카드보다 유통 핵심성이 높다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=5%, promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
