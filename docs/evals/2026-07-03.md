## Daily Eval (2026-07-03)
- Overall: **87.27** (pass)
- Operational: **92.88**
- Reader quality: **88.47** (clear; penalty=4.4, cap=100.0, reasons=clear)
- Quality gate: **87.27** (needs_iteration, editorial_below_target_bounded_penalty; editorial=83.0, operational=92.9)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=83.8, section_fit=91.7, core=66.1, commodity=100.0
- Briefing cards: 20 / Commodity cards: 42
- Sections: supply:5/5 raw=189, policy:5/5 raw=191, dist:5/5 raw=93, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.85, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=4.67, false_positive=0.00, hard_reader_issues=0, weak_core=0.50, editorial_penalty=2.5, commodity_weak=0.00, commodity_items=10, commodity_active_today=14, commodity_active_today_unlinked=4, commodity_coverage=0.30, commodity_strict_link=0.90, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.40, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.00** (target 95, needs_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=78.0, core=68.0, summary=60.0, missed=74.0, noise=70.0
- Summary: 전체 20건·섹션별 5건 충족과 신선도는 좋지만, 기사 선택은 publish-quality에는 못 미칩니다. 공급·정책에서 여름배추와 양배추 밭갈이 이슈가 반복돼 지면 효율이 떨어졌고, 유통 섹션은 판촉·교육성 행사가 코어로 올라간 점이 가장 큰 약점입니다. 병해충은 비교적 양호하지만 애호박 뿌리혹병 원인균 규명, 고추 탄저병 같은 더 구체적인 후보를 일부 놓쳤습니다. 요약문에는 ‘〈/s〉’와 중복·절단 문장이 반복돼 독자 품질을 크게 깎습니다.
- [high] duplicate_story: 정부, 여름배추 2만7000t 확보… / 배추 정부가용물량 2.7만t 확보 - 같은 장관 현장점검·2.7만t 확보 내용을 공급 섹션에서 2건 반복했다.
- [high] cross_section_duplicate: "가을 금배추 없도록"… 농식품부, 여름철 배추 생산 안정화 총력 지원 - 공급 섹션의 여름배추 기사와 사실상 같은 정책 발표다.
- [medium] cross_section_duplicate: 농산물값 폭락에 양배추밭 갈아엎은 청주 농민들... - 공급 1번 양배추 밭갈이와 같은 현장 이슈를 정책 꼬리로 재사용했다.
- [high] weak_core: [2일 경북도] 'daily 여름과일 특별전' 진행 등 - 지역 과일 판촉·할인 행사 성격이 강한데 유통 코어로 배치됐다.
- [high] weak_core: 청년 양돈농가, 공판장서 축산유통 배웠다 - 교육 행사 기사로 유통 운영·물류·시장 변화 신호가 약하다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: supply, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
