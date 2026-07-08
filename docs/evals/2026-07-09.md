## Daily Eval (2026-07-09)
- Overall: **77.62** (warn)
- Operational: **97.64**
- Reader quality: **84.00** (capped; penalty=7.0, cap=84.0, reasons=pest_theme_duplicate, commodity_false_link, commodity_false_link_severe)
- Quality gate: **77.62** (needs_major_iteration, editorial_major_issue; editorial=77.5, operational=97.6)
- Scores: completeness=100.0, diversity=100.0, summary=98.5, freshness=100.0, retrieval=90.0, section_fit=97.2, core=100.0, commodity=88.4
- Briefing cards: 20 / Commodity cards: 16
- Sections: supply:5/5 raw=222, policy:5/5 raw=190, dist:5/5 raw=68, pest:5/5 raw=39
- Metrics: title_unique=1.00, domain_diversity=0.90, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.34, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=8, commodity_active_today=11, commodity_active_today_unlinked=3, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.12, commodity_pool_false_link=0.00, commodity_dominant_section=0.75, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **77.50** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 79.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=3, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=76.0, section_fit=84.0, core=75.0, summary=88.0, missed=70.0, noise=72.0
- Summary: 분량과 신선도는 충족했지만, 병해충 섹션이 사실상 고창군 동일 보도 4건으로 채워져 일일 브리핑의 다양성과 핵심성이 크게 훼손됐다. 정책은 전국 단위 물가 점검·KREI 분석 같은 더 강한 후보를 놓치고 가격폭락 대응 보도를 중복 배치했고, 유통도 온라인도매시장 물류센터 같은 동일 이슈를 두 장으로 반복했다. 공급 섹션은 대체로 적합하나 과일류 농업관측 같은 수급 핵심 후보를 놓친 점이 아쉽다.
- [major] duplicate_story: 고창군 병해충 방제사업 관련 4건 - 16~19번이 모두 같은 고창군 3억5290만원 병해충 방제·과수화상병 예찰 보도를 반복한다.
- [major] weak_core: 고창군, 돌발해충·탄저병 등 방제 약제 농가 공급 - 핵심 카드가 직전 고창군 과수화상병 카드와 동일 사안이라 core slot을 낭비했다.
- [major] missed_candidate: 민생안정지원단, 계란·축산물 등 먹거리 물가 현장점검 - 상위 raw 후보이자 전국 단위 먹거리 물가 정책 점검인데, 지역 성명·중복 보도보다 우선순위가 높다.
- [moderate] duplicate_story: 농식품부, 농가 경영 안정을 위해 총력 대응 - 공급 1번의 가격폭락·정부 총력대응 보도와 같은 정부 대응 내용을 반복한다.
- [moderate] duplicate_story: 전국 물류허브 첫발… 호남 농산물 유통 새 판 - 12번 aT 온라인도매시장 거점물류센터와 같은 회의·시범사업을 지역 각도로 재포장한 중복 카드다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
