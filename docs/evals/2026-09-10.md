## Daily Eval (2026-09-10)
- Overall: **86.35** (pass)
- Operational: **96.23**
- Reader quality: **93.17** (clear; penalty=3.1, cap=100.0, reasons=clear)
- Quality gate: **86.35** (needs_major_iteration, editorial_major_issue; editorial=69.7, operational=96.2)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=92.5, section_fit=100.0, core=97.8, commodity=88.0
- Briefing cards: 20 / Commodity cards: 29
- Sections: supply:5/5 raw=238, policy:5/5 raw=128, dist:5/5 raw=73, pest:5/5 raw=68
- Metrics: title_unique=1.00, domain_diversity=0.80, low_tier=0.20, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.34, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=1.7, commodity_weak=0.00, commodity_items=6, commodity_active_today=18, commodity_active_today_unlinked=12, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.83, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **69.70** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 70.10; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=68.0, section_fit=82.0, core=58.0, summary=93.0, missed=61.0, noise=57.0
- Summary: 분량과 요약은 안정적이지만 정책 중복, 홍보성 꼬리 기사, 핵심 지정 오류가 크다. 특히 국가 단위 물가대책과 벼멸구 대응보다 지역 농협 소개·인삼 총채벌레를 핵심으로 둔 편집은 수정이 필요하다.
- [major] duplicate_story: 청주 내수농협, 계약농가 76명에 모종·비료 등 영농자재 지원 - 바로 앞 카드와 동일한 지원사업을 중복 보도했다.
- [moderate] promotional_filler: 동천안농협 - 변화와 혁신 통한 선제적 대응만이 경쟁력 확보 - 구체적 신규 정책보다 특정 농협의 포괄적 홍보·소개 성격이 강하다.
- [major] weak_core: 추석 물가 안정 에 900억 추가 투입… 성수품 할인 - 당일 가장 중요한 전국 단위 농축산물 물가대책인데 비핵심이다.
- [moderate] weak_core: 9월 과일류 농업관측 - 사과 출하량 19.3% 증가 전망은 지역 점검 기사보다 직접적인 수급 신호다.
- [major] weak_core: 농진청, 가을철 병해충 대응 고삐…벼멸구 방제 강화 - 여러 지역의 비래해충 급증과 전국 대응을 다룬 대표 병해충 기사다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=10%, promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
