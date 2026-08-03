## Daily Eval (2026-08-04)
- Overall: **60.55** (fail)
- Operational: **90.38**
- Reader quality: **81.70** (capped; penalty=8.7, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **60.55** (needs_major_iteration, editorial_blocking_issue; editorial=60.5, operational=90.4)
- Scores: completeness=100.0, diversity=88.0, source=40.0, summary=100.0, freshness=100.0, retrieval=82.5, section_fit=92.4, core=95.0, commodity=88.0
- Briefing cards: 20 / Commodity cards: 34
- Sections: supply:5/5 raw=305, policy:5/5 raw=62, dist:5/5 raw=70, pest:5/5 raw=21
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.30, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=2.45, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.6, commodity_weak=0.00, commodity_items=10, commodity_active_today=18, commodity_active_today_unlinked=8, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.80, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **60.55** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 63.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=3, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=61.0, section_fit=62.0, core=48.0, summary=88.0, missed=50.0, noise=57.0
- Summary: 수량과 요약은 안정적이지만, 유통 핵심에 노래교실을 배치하고 정책 중복을 허용하는 등 선택 품질이 크게 흔들렸다. 원시 후보에 스마트 APC 등 강한 유통 기사가 있었는데 지역 홍보성 카드가 이를 대체했다.
- [blocking] off_topic: 경북 상주 외서농협, 청춘힐링 노래교실 ‘성료 ’ - 조합원 여가행사로 유통·물류·판매채널과 무관하며 핵심 카드로도 지정됐다.
- [major] duplicate_story: 진병영 함양군수, 농식품부 송미령 장관 전격 면담...양파 가격 안정 및... - 같은 면담을 다룬 7번 카드와 사실상 동일한 기사다.
- [major] weak_core: 진병영 함양군수, 송미령 농식품부 장관과 면담···농정 현안 건의 - 지자체의 지원 건의 단계에 그쳐 전국적 정책 실행성이 약하다.
- [major] missed_candidate: 경북도, AI 활용해 복숭아 ·참외 선별 - 1433억원 규모 스마트 APC 구축은 구체적인 산지유통 운영 기사인데 선택되지 않았다.
- [moderate] promotional_filler: 서충주농협 라이브커머스로 '하늘작 충주 복숭아 ' 400상자 전량 판매 - 소량 완판과 품질 홍보 중심이며 원시 후보의 APC 혁신·납품계약 기사보다 약하다.

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
