## Daily Eval (2026-08-31)
- Overall: **63.35** (fail)
- Operational: **92.09**
- Reader quality: **91.91** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **63.35** (needs_major_iteration, editorial_blocking_issue; editorial=63.4, operational=92.1)
- Scores: completeness=100.0, diversity=82.1, source=100.0, summary=98.5, freshness=90.0, retrieval=90.5, section_fit=100.0, core=84.6, commodity=77.5
- Briefing cards: 20 / Commodity cards: 23
- Sections: supply:5/5 raw=323, policy:5/5 raw=93, dist:5/5 raw=62, pest:5/5 raw=29
- Metrics: title_unique=1.00, domain_diversity=0.45, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.38, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=6, commodity_active_today=12, commodity_active_today_unlinked=6, commodity_coverage=0.18, commodity_strict_link=0.67, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **63.35** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 64.50; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=2, major=2, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=61.0, section_fit=63.0, core=62.0, summary=89.0, missed=48.0, noise=57.0
- Summary: 형식과 카드 수는 충족했지만, 강한 유통·병해충 후보를 놓치고 수상·행사성 기사와 범위 밖 pest 기사를 채웠다. 특히 dist와 pest는 일일 브리핑으로 수용하기 어려운 선택 결함이 있다.
- [blocking] off_topic: "품종 개발로 끝나선 안 된다"…김대현 원예원장이 '시장'을 보는 이유 - 신품종 산업화·유통 기사로 병해충이나 생육 위험이 아니다.
- [blocking] off_topic: 중국산 ‘발암 배추’에 난리난 한국 - 중국 현지 식품안전 사건으로 국내 작물 병해충·생육 위험과 무관하다.
- [major] missed_candidate: 농업법인·농협이 못 받은 홈플러스 납품대금 1000억 넘어 - 농가·농협의 대규모 유통채권 위험을 다룬 핵심 기사인데 수상 기사보다 현저히 중요하다.
- [major] promotional_filler: 이효진 동문경농협 조합장, BEST 경제 CEO상 수상 - 개인 수상 소식으로 유통 운영 정보가 거의 없고 강한 후보를 밀어냈다.
- [moderate] missed_candidate: [다중재해 시대] 극한 기상에 널뛴 농산물 시세…기술·전략으로 활로 찾아 - 시세 변동과 공급·상품화 대응을 구체적으로 다뤄 단순 수출 방문·선적식보다 실용적이다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
