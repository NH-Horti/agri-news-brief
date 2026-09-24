## Daily Eval (2026-07-09)
- Overall: **95.72** (pass)
- Operational: **96.67**
- Reader quality: **96.49** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **95.72** (needs_iteration, editorial_acceptance_gate_failed; editorial=84.9, operational=96.7)
- Scores: completeness=100.0, diversity=96.4, source=100.0, summary=97.0, freshness=100.0, retrieval=90.0, section_fit=100.0, core=82.0, commodity=99.1
- Briefing cards: 20 / Commodity cards: 11
- Sections: supply:5/5 raw=180, policy:5/5 raw=138, dist:5/5 raw=59, pest:5/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.65, low_tier=0.15, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=4.48, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=8, commodity_active_today=11, commodity_active_today_unlinked=3, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.90** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 87.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=86.0, section_fit=88.0, core=89.0, summary=78.0, missed=82.0, noise=84.0
- Summary: 섹션별 5건을 모두 채웠고 핵심 이슈인 과일 관측, 농산물 가격 폭락·물가 대응, 온라인도매 물류, 과수화상병 예찰은 대체로 잘 잡았다. 다만 정책 섹션에 사진 에세이성 약한 카드가 들어가 더 강한 가격안정제 시행 기사 등을 놓쳤고, 일부 요약은 스크래핑 문구·잘림이 그대로 남아 독자 사용성이 떨어진다. 유통·병해충의 후순위 카드는 원자료 풀이 약한 점을 감안하면 허용 가능하나 지역 행사·관리 당부성 filler가 다소 많다.
- [moderate] missed_candidate: 농산물 가격 하락분 지원… 가격안정제 도입 - 가격폭락 대응과 직접 연결되는 정책 시행 기사인데 약한 B컷 카드에 밀렸다.
- [moderate] noise: 자식처럼 키운 농산물 제값 찾고 싶은 농민들[금주의 B컷] - 사진 에세이 성격이 강하고 정책 정보량이 낮아 농정 브리핑 카드로 약하다.
- [moderate] bad_summary: "취약계층, 농식품 물가 상승 직격탄 맞아" - 요약에 '생활 필 일률적...'처럼 잘린 원문과 스크래핑 잔여 문구가 섞였다.
- [moderate] bad_summary: 7월 과일류 농업관측 - 요약이 기사 본문 앞부분을 붙여온 형태라 사과·배·복숭아 전망의 핵심 수치가 정리되지 않는다.
- [minor] bad_summary: 온라인 도매시장 , 4대 권역 거점물류센터 구축…물류 효율화 - 요약 말미에 Internet Explorer 안내 문구가 포함됐다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
