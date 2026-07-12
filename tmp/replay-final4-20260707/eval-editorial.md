## Daily Eval (2026-07-07)
- Overall: **94.47** (pass)
- Operational: **97.51**
- Reader quality: **97.51** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **94.47** (needs_iteration, editorial_major_issue; editorial=80.8, operational=97.5)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=98.5, freshness=100.0, retrieval=87.5, section_fit=100.0, core=100.0, commodity=89.4
- Briefing cards: 20 / Commodity cards: 44
- Sections: supply:5/5 raw=250, policy:5/5 raw=109, dist:5/5 raw=84, pest:5/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.80, low_tier=0.20, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.45, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=11, commodity_active_today=14, commodity_active_today_unlinked=3, commodity_coverage=0.33, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.73, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **80.85** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 82.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=83.0, core=86.0, summary=80.0, missed=76.0, noise=78.0
- Summary: 분량은 4개 섹션 모두 5건으로 충족했고 핵심 수급·유통·과수화상병 이슈는 대체로 잡았다. 다만 과수화상병 나주 대응을 두 번 실어 pest 섹션 품질이 크게 떨어졌고, supply에는 정책성 농민단체 집회 기사가 들어가 policy 카드와 주제가 겹친다. dist의 마늘 경매 포토성 기사와 일부 잘린/잡음 섞인 요약도 일간 브리핑 완성도를 낮춘다.
- [major] duplicate_story: 나주시, ' 과수화상병 4차 약제' 긴급 공급... 유입 차단 총력 - 직전 카드인 뉴시스 나주 과수화상병 4차 약제 공급 기사와 같은 사안이다.
- [moderate] wrong_section: "생산비 폭등·농산물값 폭락 더는 못 버틴다" - 수급·가격 데이터보다 농민단체 집회·농정 요구 성격이 강하고 policy 카드와 주제도 중복된다.
- [moderate] duplicate_theme: "가격 폭락·농자재 폭등·CPTPP까지"···3중 악재에 농업계 거센 반발 - supply의 전농 집회 카드와 같은 농산물값 폭락·농자재값 폭등 항의 테마가 반복된다.
- [moderate] noise: '햇마늘이 한가득'…경북 영천 마늘 경매 - 연합뉴스 사진 캡션 수준으로 유통 운영·가격·물량 정보가 거의 없고 UI 문구가 요약에 섞였다.
- [moderate] missed_candidate: "판로 걱정 덜겠다"... 고흥군 스마트 공급센터, 농산물 유통 거점 기대 - 선별·포장·저장·출하까지 포함한 물류 거점 기사로 포토 경매 카드보다 운영성이 높다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
