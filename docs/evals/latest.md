## Daily Eval (2026-08-31)
- Overall: **81.19** (warn)
- Operational: **90.47**
- Reader quality: **87.05** (clear; penalty=3.4, cap=100.0, reasons=clear)
- Quality gate: **81.19** (needs_major_iteration, editorial_major_issue; editorial=68.5, operational=90.5)
- Scores: completeness=100.0, diversity=89.3, source=100.0, summary=100.0, freshness=90.0, retrieval=90.5, section_fit=91.7, core=79.7, commodity=77.5
- Briefing cards: 20 / Commodity cards: 23
- Sections: supply:5/5 raw=323, policy:5/5 raw=94, dist:5/5 raw=59, pest:5/5 raw=29
- Metrics: title_unique=1.00, domain_diversity=0.55, low_tier=0.15, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.51, false_positive=0.00, hard_reader_issues=0, weak_core=0.10, editorial_penalty=1.9, commodity_weak=0.00, commodity_items=6, commodity_active_today=12, commodity_active_today_unlinked=6, commodity_coverage=0.18, commodity_strict_link=0.67, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **68.55** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 69.80; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=68.0, section_fit=75.0, core=59.0, summary=88.0, missed=54.0, noise=72.0
- Summary: 형식과 기사 수는 충족했지만 핵심 선정력이 약하다. 특히 유통의 홈플러스 미수금·시세 변동 기사와 병해충의 구체적 경보를 놓치고, 지역 행사·지원 및 일반 호우 기사를 핵심으로 올렸다.
- [major] missed_candidate: 농업법인·농협이 못 받은 홈플러스 납품대금 1000억 넘어 - 전국 유통망 위기와 농업계 자금 피해가 구체적인 최상위 운영 이슈다.
- [moderate] wrong_section: 농지 전수조사 부작용·영농형태양광 수익 ‘도마’ - 온라인도매시장 언급은 일부뿐이며 중심은 농지·국정감사 정책 현안이다.
- [moderate] missed_candidate: [다중재해 시대] 극한 기상에 널뛴 농산물 시세…기술·전략으로 활로 - 시세 변동, 공급 확대, 비정형 농산물 상품화 등 유통 현장 정보가 풍부하다.
- [major] weak_core: 새벽 집중호우에 일부 지역 침수...가뭄엔 '단비' - 구체적인 작물 피해나 방제 조치보다 일반 기상 상황과 농가 기대를 전한다.
- [moderate] missed_candidate: 비 그친 뒤 단감 탄저병 주의… 적기 방제 서둘러야 - 강우 뒤 발생 위험과 방제 시점을 제시하는 명명 병해 경보다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
