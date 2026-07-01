## Daily Eval (2026-07-02)
- Overall: **85.47** (pass)
- Operational: **95.72**
- Reader quality: **86.77** (capped; penalty=8.9, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **85.47** (needs_iteration, editorial_below_target_bounded_penalty; editorial=82.0, operational=95.7)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=87.5, section_fit=97.2, core=100.0, commodity=96.1
- Briefing cards: 20 / Commodity cards: 22
- Sections: supply:5/5 raw=172, policy:5/5 raw=190, dist:5/5 raw=81, pest:5/5 raw=30
- Metrics: title_unique=1.00, domain_diversity=0.70, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.87, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.8, commodity_weak=0.00, commodity_items=7, commodity_active_today=12, commodity_active_today_unlinked=5, commodity_coverage=0.21, commodity_strict_link=0.86, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=82.0, core=78.0, summary=91.0, missed=76.0, noise=78.0
- Summary: 형식과 카드 수는 모두 충족했지만, 편집 품질은 목표 95에는 크게 못 미칩니다. 핵심 이슈인 마늘 가격·정부 물가대책·수입농산물 협의체·화상병 대응은 잡았으나, 같은 사건을 중복 배치하거나 사진성/인물성/취임식성 기사를 핵심 또는 꼬리 카드로 넣은 문제가 큽니다. 특히 pest의 보은군수 취임 기사는 병해충 섹션에서 명백한 오선정이며, dist의 합천 마늘 산지경매 2건 중복은 더 나은 물류·수출·APC 후보를 밀어냈습니다.
- [high] irrelevant_selection: 보은군, 최재형 군수 취임식 생략한 채 민선 9기 민생 행보 본격화 - 병해충 내용이 아니라 지자체장 취임·군정 기사다.
- [high] duplicate_story: 합천군, 2026년산 건 마늘 초매식… / 합천군, 건마늘 산지경매 개장 - 같은 합천 건마늘 산지경매 개장 내용을 두 카드로 반복했다.
- [medium] weak_core: '올해 마늘값은 괜찮나?' - 1번 창녕 마늘 가격 기사와 같은 현장의 사진성 보조 기사로 보이며 핵심 카드로 약하다.
- [medium] duplicate_story: 백성익 (사)제주 감귤 연합회장, 수입농산물 관리 민관협의체 위원 선정 - 수입농산물 민관협의체 출범 카드와 사실상 같은 이슈의 지역 인물 후속이다.
- [medium] cross_section_overlap: 정부, 농축산물 할인에 3천억 투입… / 계란 2억개 더 들여온다… - 정부 여름 물가·할인·계란수입 대책을 policy와 dist에 중복 배치했다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
