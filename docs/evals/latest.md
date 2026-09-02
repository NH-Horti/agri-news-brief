## Daily Eval (2026-09-03)
- Overall: **88.05** (pass)
- Operational: **96.23**
- Reader quality: **96.05** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **88.05** (needs_major_iteration, editorial_major_issue; editorial=60.5, operational=96.2)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=90.6, section_fit=88.8, core=79.8, commodity=96.8
- Briefing cards: 20 / Commodity cards: 49
- Sections: supply:5/5 raw=320, policy:5/5 raw=189, dist:5/5 raw=87, pest:5/5 raw=34
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.10, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=4.09, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=9, commodity_active_today=13, commodity_active_today_unlinked=4, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.56, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **60.55** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 62.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=5, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=58.0, section_fit=66.0, core=61.0, summary=84.0, missed=47.0, noise=43.0
- Summary: 분량과 최신성은 충족했지만 샤인머스캣 한 이슈가 공급·유통 8개 카드를 잠식했다. 유통에는 정책 기사와 수상 홍보물이 섞였고, 병해충은 외래·비래해충 핵심 후보를 놓쳐 편집 품질이 낮다.
- [major] duplicate_theme: 샤인머스캣 관련 공급 기사 4건 - 가격 하락·출하 집중이라는 동일 주제가 공급 5건 중 4건을 차지한다.
- [major] duplicate_story: 샤인머스캣…“조기출하 줄여 제 값 받을 수 있게 품질관리 강화” - 같은 경북도 대책회의가 공급 1건과 유통 3건에서 반복된다.
- [moderate] wrong_section: 농산물가격안정제 Q&A - 손실보전 제도 설명은 유통 운영보다 정책에 직접 해당한다.
- [moderate] promotional_filler: 상주 중화 농협 공선 출하 회, GAP 우수사례 경진대회 금상 - 수상 소식 중심으로 당일 유통 변화나 시장 영향이 약하다.
- [major] weak_core: 충남도의회 5분발언서 스마트팜 수익성·재선충 방제 대책 촉구 - 복수 의제를 묶은 의회 발언이며 요약도 스마트팜 수익성에 치우쳐 병해충 핵심성이 낮다. 코어에서 내려야 한다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
