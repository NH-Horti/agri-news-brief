## Daily Eval (2026-10-12)
- Overall: **90.35** (warn)
- Operational: **94.63**
- Reader quality: **93.73** (clear; penalty=0.9, cap=100.0, reasons=clear)
- Quality gate: **90.35** (needs_major_iteration, editorial_major_issue; editorial=73.5, operational=94.6)
- Scores: completeness=100.0, diversity=97.6, source=100.0, summary=100.0, freshness=94.3, retrieval=83.2, section_fit=100.0, core=73.7, commodity=90.9
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=411, policy:5/5 raw=100, dist:5/5 raw=115, pest:5/5 raw=23
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.15, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.22, false_positive=0.00, hard_reader_issues=0, weak_core=0.20, editorial_penalty=0.5, commodity_weak=0.00, commodity_items=13, commodity_active_today=18, commodity_active_today_unlinked=5, commodity_coverage=0.39, commodity_strict_link=0.92, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.69, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **73.50** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 76.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=74.0, section_fit=72.0, core=68.0, summary=91.0, missed=63.0, noise=75.0
- Summary: 형식과 기사 수, 요약 품질은 좋지만 정책·병해충 섹션의 선별력이 약하다. 특히 최상위 과수화상병 후보를 누락하고 잔류농약 조사와 상품 중심 방제 기사를 채운 점, 정책에 수출·해외 물가 기사를 배치한 점이 일일 브리핑 완성도를 낮춘다.
- [major] missed_candidate: 이재관 의원 "과수화상병 폐원 기준 합리화해야" - 병해충 풀의 최상위 후보이자 과수화상병 대응 기준을 다룬 핵심 기사인데 누락됐다.
- [moderate] wrong_section: 중동 맞춤형 ‘K-떡볶이’ 수출 40억원 달성…비법은? - 정책 변화보다 수출 성과와 상품 기술을 다룬 유통·수출 기사다.
- [moderate] wrong_section: 유럽 가뭄 뒤 올리브유값 급등, 호주 홍수 뒤 상추 값 치솟아…‘기후 인플레이션’ 심각 - 국내 농정 조치가 없는 해외 식품가격 동향으로 정책 섹션 적합도가 낮다.
- [moderate] wrong_section: 농관원, 배추ㆍ무 등 김장 채소류 잔류농약 조사 - 병해충 위험이나 방제가 아니라 출하 농산물의 안전성 검사 기사다.
- [moderate] promotional_filler: 시설 하우스 잿빛곰팡이병 미리 방제 해야 효과적 - 유용한 방제 정보가 있으나 특정 업체 약제 제안에 크게 의존해 홍보성이 강하다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
