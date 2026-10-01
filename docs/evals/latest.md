## Daily Eval (2026-09-17)
- Overall: **82.88** (warn)
- Operational: **90.15**
- Reader quality: **86.37** (clear; penalty=3.8, cap=100.0, reasons=clear)
- Quality gate: **82.88** (needs_major_iteration, editorial_major_issue; editorial=73.0, operational=90.2)
- Scores: completeness=100.0, diversity=88.0, source=40.0, summary=100.0, freshness=100.0, retrieval=78.5, section_fit=92.4, core=89.1, commodity=88.0
- Briefing cards: 20 / Commodity cards: 44
- Sections: supply:5/5 raw=237, policy:5/5 raw=113, dist:5/5 raw=57, pest:5/5 raw=19
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.30, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=2.86, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=8, commodity_active_today=15, commodity_active_today_unlinked=7, commodity_coverage=0.24, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.88, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **73.05** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 73.80; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=72.0, section_fit=72.0, core=76.0, summary=88.0, missed=61.0, noise=67.0
- Summary: 형식과 카드 수는 충족했지만, 정책·유통 섹션의 오배치와 약한 지역성 꼬리 기사, 동일 배추 저장 연구의 중복이 품질을 낮췄다. 특히 유통 후보군에 더 강한 물류·수출 기사가 있는데도 이를 놓쳤다.
- [moderate] duplicate_theme: [같이경제] 추석 물가 …한우 오르고 과일 내리고 - 차례상 물가 기사 3건이 겹쳐 공급 섹션의 정보 폭이 좁다.
- [moderate] wrong_section: 추석 차례상, 전통시장이 더 저렴해 - 정책보다 가격 동향을 다룬 공급 기사이며 구체적 정책 조치가 약하다.
- [major] duplicate_story: 농진청, 정부 비축 봄 배추 장기 저장 가능성 확인 - 유통 섹션의 ‘봄배추 장기 저장’과 동일한 농진청 실증연구다.
- [moderate] noise: 정선 임계농협 농산물산지유통 센터에 비상소화장치 설치 - 시설 안전 단신으로 유통 운영·물류 변화에 대한 편집 가치가 낮다.
- [moderate] promotional_filler: 송미령 농식품부 장관, 추석 앞두고 전통주 농촌창업 현장 방문 - 장관 현장 방문과 지원 홍보가 중심이며 구체적인 유통 성과가 부족하다.

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
