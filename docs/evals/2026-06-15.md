## Daily Eval (2026-06-15)
- Overall: **92.76** (pass)
- Operational: **94.61**
- Reader quality: **93.86** (capped; penalty=0.8, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **92.76** (needs_iteration, editorial_below_target_bounded_penalty; editorial=84.0, operational=94.6)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=90.0, retrieval=86.9, section_fit=100.0, core=86.3, commodity=96.8
- Briefing cards: 19 / Commodity cards: 21
- Sections: supply:5/5 raw=246, policy:4/5 raw=124, dist:5/5 raw=47, pest:5/5 raw=36
- Metrics: title_unique=1.00, domain_diversity=0.79, summary_presence=1.00, summary_numeric=0.68, fresh_72h=1.00, fit_avg=4.03, false_positive=0.00, hard_reader_issues=0, weak_core=0.20, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=9, commodity_active_today=15, commodity_active_today_unlinked=6, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.56, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=82.0, section_fit=86.0, core=84.0, summary=91.0, missed=79.0, noise=81.0
- Summary: 전반적으로 읽을 만한 브리핑이지만, 고득점 수준의 편집 선택이라고 보긴 어렵다. 핵심 기사 몇 개는 적절했으나 공급·유통 섹션에서 일본 도매시장 시리즈 중복성, 지역 출하·소비촉진성 꼬리기사 비중, 정책 섹션 1건 부족이 눈에 띈다. 특히 공급은 더 강한 수급/가격 구조 기사 후보가 있었고, 유통은 온라인도매시장 비판 기사 같은 더 직접적인 운영 이슈를 놓쳤다. 병해충은 화상병 중심축은 맞지만 우박 기사 2건은 중복·비병해충 성격이 강하다.
- [high] missed_opportunity: 온라인도매시장, 왜 나랏돈 퍼주는 '곳간' 됐나 - 유통 구조·운영성 더 강한 후보를 누락했다.
- [high] weak_selection: [픽! 영동] 금강 모래밭서 생산된 '양산수박' 출하 - 단순 지역 출하 소식으로 수급 의제성이 약하다.
- [medium] promotional_filler: 농협유통 하나로마트, ' 양배추 ' 소비 촉진행사...농촌과 상생 협력 - 행사성 소비촉진 기사로 편집 밀도가 낮다.
- [medium] duplication: 오타도매시장 / 요코하마도매시장 - 일본 도매시장 사례가 유사해 정보 중복감이 있다.
- [medium] wrong_section_tone: “ 배추 수확 앞두고 쑥대밭” 강원농가 덮친 우박 피해 속출 - 재해 피해 기사로 병해충 섹션 적합성이 약하다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
