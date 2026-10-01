## Daily Eval (2026-09-22)
- Overall: **88.37** (warn)
- Operational: **93.95**
- Reader quality: **90.53** (clear; penalty=3.4, cap=100.0, reasons=clear)
- Quality gate: **88.37** (needs_major_iteration, editorial_major_issue; editorial=78.3, operational=94.0)
- Scores: completeness=100.0, diversity=98.4, source=100.0, summary=100.0, freshness=100.0, retrieval=75.5, section_fit=97.2, core=85.0, commodity=90.0
- Briefing cards: 20 / Commodity cards: 27
- Sections: supply:5/5 raw=238, policy:5/5 raw=130, dist:5/5 raw=113, pest:5/5 raw=11
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.10, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.52, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=1.9, commodity_weak=0.00, commodity_items=7, commodity_active_today=12, commodity_active_today_unlinked=5, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.71, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **78.35** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 78.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=78.0, section_fit=88.0, core=82.0, summary=86.0, missed=65.0, noise=66.0
- Summary: 전 섹션 5건과 시의성은 확보했지만, 정책 섹션이 추석 차례상 비용·할인 효과 기사로 과도하게 중복됐다. 유통의 현장 방문성 기사와 병해충의 간담회·일반 해설도 정보 밀도를 낮춘다.
- [major] duplicate_theme: 1930억 투입해 추석 차례상 비용 9년 만에 낮췄다 - 6번 기사와 차례상 비용 하락 및 할인 재정 효과가 사실상 동일하다.
- [moderate] duplicate_theme: 추석 1주일 전 기준 차례상 비용 전년比 1.5% 하락 - 차례상 비용 하락 주제가 정책 5건 중 3건을 차지한다.
- [moderate] promotional_filler: 충북농협, 괴산 군자농협 사과 출하 현장 점검 - 단순 방문·점검 중심이며 물량, 가격, 물류 차질 등 새로운 운영 정보가 부족하다.
- [moderate] noise: 임미애 의원, 과수 무병묘 생산기반 강화 현장 의견 청취 - 정책간담회 개최 사실이 중심이며 구체적인 병해 위험이나 방제 조치가 없다.
- [moderate] noise: 뙤약볕에 타들어 가는 농심...과일도 화상 입는다 '일소현상' [지식용어...] - 일반적인 용어 해설로, 같은 섹션의 실제 폭염 피해·복구 기사보다 현장성이 낮다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
