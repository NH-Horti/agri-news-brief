## Daily Eval (2026-07-09)
- Overall: **94.37** (pass)
- Operational: **96.90**
- Reader quality: **96.72** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **94.37** (needs_iteration, editorial_major_issue; editorial=83.6, operational=96.9)
- Scores: completeness=100.0, diversity=88.9, source=80.0, summary=100.0, freshness=100.0, retrieval=90.0, section_fit=100.0, core=100.0, commodity=96.1
- Briefing cards: 20 / Commodity cards: 12
- Sections: supply:5/5 raw=180, policy:5/5 raw=138, dist:5/5 raw=59, pest:5/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.20, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.84, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=7, commodity_active_today=11, commodity_active_today_unlinked=4, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.60** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 84.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=85.0, section_fit=88.0, core=80.0, summary=85.0, missed=80.0, noise=84.0
- Summary: 전체 4개 섹션 모두 5건을 채워 기본 완성도는 높고, 물가·수급·온라인도매 물류·병해충 대응 등 주요 축도 대체로 포착했다. 다만 병해충 섹션에서 고창군 방제 기사가 사실상 중복으로 2건, 그것도 모두 core로 들어간 점이 가장 큰 결함이다. 유통 섹션도 온라인도매 물류 같은 강한 기사 옆에 지역 협약·초매식성 filler가 남아 있고, 가격 폭락·대책 테마가 supply/policy에 다소 과밀하다. 몇몇 요약에는 원문 스크랩 흔적이 있어 독자용 브리핑 품질을 낮춘다.
- [major] duplicate_story: 고창군 과수화상병 청정 유지 / 고창군, 주요 농작물 병해충 선제 방제 순항 - 두 기사가 같은 고창군 병해충 방제사업과 과수화상병 청정 유지 내용을 반복하며 둘 다 core로 선정됐다.
- [moderate] missed_candidate: 나주시, 배·사과 농가에 과수화상병 방제 약 추가 지원 - 과수화상병 확산 대응 성격이 뚜렷한 후보인데 고창 중복 기사에 밀렸다.
- [moderate] promotional_filler: 합천유통·사과대추 공선출하회, 공동 출하 협약 - 지역 협약식 중심의 약한 판로 홍보 기사로, 전국 유통 운영 관점의 가치가 제한적이다.
- [minor] promotional_filler: 대관령원예농협, 산지공판장 초매식 개최 - 고랭지 농산물 출하 개시 정보는 있으나 초매식 행사 비중이 커 핵심 유통 기사로는 약하다.
- [moderate] duplicate_theme: 농자재값 폭등·농산물 가격 폭락 / 농산물 가격 폭락에 농민 울분 / 농산물 가격안정제 도입 - 농산물 가격 폭락과 정부 대응 테마가 여러 카드에 반복돼 섹션 다양성이 줄었다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
