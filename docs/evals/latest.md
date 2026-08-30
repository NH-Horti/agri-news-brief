## Daily Eval (2026-08-31)
- Overall: **79.10** (warn)
- Operational: **91.60**
- Reader quality: **87.10** (clear; penalty=4.5, cap=100.0, reasons=clear)
- Quality gate: **79.10** (needs_major_iteration, editorial_major_issue; editorial=63.5, operational=91.6)
- Scores: completeness=100.0, diversity=92.9, source=100.0, summary=98.5, freshness=90.0, retrieval=90.5, section_fit=100.0, core=84.4, commodity=77.5
- Briefing cards: 20 / Commodity cards: 23
- Sections: supply:5/5 raw=323, policy:5/5 raw=94, dist:5/5 raw=59, pest:5/5 raw=29
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.15, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.42, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.5, commodity_weak=0.00, commodity_items=6, commodity_active_today=12, commodity_active_today_unlinked=6, commodity_coverage=0.18, commodity_strict_link=0.67, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **63.45** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 65.10; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=4, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=61.0, section_fit=68.0, core=57.0, summary=88.0, missed=48.0, noise=62.0
- Summary: 수량과 요약 품질은 좋지만, 유통의 핵심 현안을 놓치고 홍보성 기사를 채택했으며 병해충에 식품안전·품종산업 기사가 섞였다. 핵심 카드 지정도 지역 지원 사례에 치우쳐 재선정이 필요하다.
- [major] missed_candidate: 농업법인·농협이 못 받은 홈플러스 납품대금 1000억 넘어 - 납품대금 차질은 농가·농협에 직접 영향을 주는 전국급 유통 현안인데 제외됐다.
- [major] missed_candidate: 경남농협, 막혔던 대중 단감 수출 길 17년 만에 다시 잇는다 - 검역협상 타결에 따른 수출 재개는 4톤 선적식보다 파급력이 크다.
- [moderate] promotional_filler: 이효진 동문경농협 조합장, BEST 경제 CEO상 수상 - 인물 수상 소식으로 유통 운영이나 시장 변화 정보가 거의 없다.
- [moderate] promotional_filler: 매출 86% 늘린 AI 농산물 유통기업…농식품부, 'A-벤처스' 선정 - 기업 선정 홍보 성격이 강하고 구체적인 유통 운영 변화가 부족하다.
- [major] wrong_section: 중국산 ‘발암 배추’에 난리난 한국… - 포름알데히드 사용 논란은 병해충·생육 위험이 아니라 수입 식품안전 사안이다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=15%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
