## Daily Eval (2026-07-07)
- Overall: **70.05** (warn)
- Operational: **96.04**
- Reader quality: **87.30** (capped; penalty=8.7, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **70.05** (needs_major_iteration, editorial_blocking_issue; editorial=70.0, operational=96.0)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=87.5, section_fit=100.0, core=100.0, commodity=93.3
- Briefing cards: 20 / Commodity cards: 51
- Sections: supply:5/5 raw=250, policy:5/5 raw=109, dist:5/5 raw=84, pest:5/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.90, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.76, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.6, commodity_weak=0.00, commodity_items=11, commodity_active_today=14, commodity_active_today_unlinked=3, commodity_coverage=0.33, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.64, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **70.05** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 70.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=6, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=70.0, section_fit=75.0, core=68.0, summary=88.0, missed=60.0, noise=55.0
- Summary: 분량은 4개 섹션 모두 5건으로 충족했고 요약도 대체로 사실과 수치 전달은 좋다. 그러나 정책 섹션에 농업 무관 ‘인물 동정’이 들어갔고, 정책·유통·병해충에서 같은 이슈를 반복 선정했다. 특히 병해충 5건 중 3건이 나주 과수화상병 동일 기사라 섹션 큐레이션 품질이 크게 떨어진다. 유통·정책 쪽에서는 수출검역 확대, 민생물가 대책 등 더 강한 후보를 놓치고 지역 행사성·홍보성 꼬리기사를 채웠다.
- [blocking] off_topic: 인물 동정 (7월 7일) - 충북 단체장 일정과 SK하이닉스 투자지원 내용으로 농업 정책 브리핑과 실질 관련성이 거의 없다.
- [major] duplicate_story: 나주시 과수화상병 유입 차단 3건 - 16·17·18번이 모두 나주시 4차 방제약제 공급이라는 같은 보도다. 병해충 섹션 5칸 중 3칸을 동일 이슈가 차지했다.
- [major] duplicate_story: "가격 폭락·농자재 폭등·CPTPP까지" / "반값 농자재·농가소득 안전망 구축 시급" - 두 기사 모두 한종협 6일 기자회견과 같은 요구안을 다룬 동일 스토리다.
- [major] duplicate_story: 농산물값 하락에… 화천군수 직접 세일즈 / 농산물 유통·복지·온라인몰로 강원 경제 '돌파구' - 화천군수 가락시장 세일즈와 오이·애호박 가격 급락 대응 내용이 섹션을跨어 반복된다.
- [major] weak_core: 농산물값 하락에… 화천군수 직접 세일즈 - 지자체장의 현장 판촉 행보로 정책 코어로 보기 어렵고 행사성 지역 기사 성격이 강하다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
