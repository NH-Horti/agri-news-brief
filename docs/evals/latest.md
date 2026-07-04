## Daily Eval (2026-07-03)
- Overall: **95.40** (pass)
- Operational: **96.50**
- Reader quality: **96.50** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **95.40** (needs_iteration, editorial_below_target_bounded_penalty; editorial=84.0, operational=96.5)
- Scores: completeness=100.0, diversity=100.0, summary=86.5, freshness=100.0, retrieval=83.8, section_fit=100.0, core=100.0, commodity=99.1
- Briefing cards: 20 / Commodity cards: 42
- Sections: supply:5/5 raw=189, policy:5/5 raw=191, dist:5/5 raw=93, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.85, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=5.10, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=10, commodity_active_today=14, commodity_active_today_unlinked=4, commodity_coverage=0.30, commodity_strict_link=0.90, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=82.0, core=81.0, summary=74.0, missed=79.0, noise=77.0
- Summary: 분량과 신선도는 충족했지만, 정책·유통 섹션에서 중복 물가 기사와 정책성 기사, 교육·행사성 filler가 강한 후보를 밀어냈다. 공급과 병해충은 대체로 쓸 만하나 일부 소비자 할인/지역 지원성 카드와 조악한 요약 때문에 publish-quality에는 못 미친다.
- [major] bad_summary: 정부 “최고 가격 제 없었다면 6월 물가 상승률 3.2% 아닌 3.6%” - 요약이 공유 버튼·URL 문구로 채워져 독자 정보가 거의 없다.
- [major] duplication: 24% 뛴 유가發 도미노 인상… 공업품·밥상물가 다 올랐다 - 앞선 최고가격제/6월 물가 카드와 같은 물가 총론을 반복한다.
- [major] wrong_section: 정부, 농축산물 할인에 3000억원 투입…농할상품권 월 200억원 발행 - 유통 운영보다 정책·할인지원 성격이 강하고 policy 카드와 내용이 겹친다.
- [major] filler: 청년 양돈농가, 공판장 서 축산유통 배웠다 - 교육 행사성 기사로 유통·물류·시장운영 뉴스 가치가 낮다.
- [moderate] weak_tail: 한 통에 9500원! ' 수박 오픈런'…고물가 속 '최저가' 찾기 - 소비자 할인 현장 중심이고 요약도 방송 원문식으로 수급 정보가 약하다.

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: supply, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
