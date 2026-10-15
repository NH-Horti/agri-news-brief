## Daily Eval (2026-10-16)
- Overall: **89.15** (warn)
- Operational: **95.66**
- Reader quality: **90.00** (capped; penalty=4.7, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **89.15** (needs_major_iteration, editorial_acceptance_gate_failed; editorial=78.6, operational=95.7)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=73.6, section_fit=95.8, core=100.0, commodity=88.0
- Briefing cards: 20 / Commodity cards: 36
- Sections: supply:5/5 raw=360, policy:5/5 raw=82, dist:5/5 raw=91, pest:5/5 raw=11
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.20, summary_presence=1.00, summary_numeric=0.65, fresh_72h=1.00, fit_avg=3.87, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=5, commodity_active_today=12, commodity_active_today_unlinked=7, commodity_coverage=0.15, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.80, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **78.60** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 79.80; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=77.0, section_fit=80.0, core=72.0, summary=89.0, missed=76.0, noise=82.0
- Summary: 20건 구성과 요약은 안정적이지만, 공급 핵심기사와 정책 코어 지정이 약하고 유통에서 동일한 도매시장 휴업 이슈를 중복 선택했다. 강한 후보가 있는데도 지역성·기획성 꼬리기사가 일부 자리를 차지했다.
- [moderate] weak_core: 충남세종농협, 쪽파가격 하락에 농가 지원 나서 - 지역 직거래장터 할인행사 중심이라 전국 수급 핵심기사로는 약하다.
- [moderate] wrong_section: [진단과 제언] K푸드의 길 ⋯ 지역 지키는 농업 - 생산·가격 수급보다 판로와 유통 기반에 관한 제언이다.
- [moderate] weak_core: 농산물가격안정제 첫 시행…관건은 ‘선제적 수급 관리’ - 첫 시행되는 전국 가격안정제는 민간창고 해명 기사보다 정책 중요도가 높다.
- [moderate] promotional_filler: 예산군, 학교급식에 지역 농산물 더하고 계절근로자 행정 부담 던다 - 지역 회의·단가 확정 중심이며 정책 파급력이 제한적이다.
- [moderate] duplicate_theme: [농담] 유통혁신 외치는데 도매시장은 동시휴업…농민 출하권 누가 지키... - 앞 카드와 동일한 가락·구리시장 동시휴업 및 출하 차질을 반복한다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
