## Daily Eval (2026-08-06)
- Overall: **78.89** (warn)
- Operational: **93.05**
- Reader quality: **86.89** (capped; penalty=6.2, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **78.89** (needs_major_iteration, editorial_major_issue; editorial=61.1, operational=93.0)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=86.2, section_fit=85.6, core=77.2, commodity=88.0
- Briefing cards: 20 / Commodity cards: 26
- Sections: supply:5/5 raw=257, policy:5/5 raw=64, dist:5/5 raw=30, pest:5/5 raw=44
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.20, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.42, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=1.2, commodity_weak=0.00, commodity_items=8, commodity_active_today=15, commodity_active_today_unlinked=7, commodity_coverage=0.24, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=1.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **61.10** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 61.10; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=5, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=62.0, section_fit=58.0, core=60.0, summary=84.0, missed=52.0, noise=45.0
- Summary: 분량과 요약은 충실하지만 정책·유통 섹션의 오배치, 병해충 기사 중복, 폭염 물가 테마 과잉이 심하다. 원문 풀에 있는 정책·시장운영 후보를 놓쳐 일일 브리핑으로는 재편이 필요하다.
- [major] duplicate_story: 경기 농기원, 과수 병해충·생리장해 예방 관리 각별한 주의 당부 / 경기도 "폭염·고온다습에 작목별 선제적 병해충·생리장해 예방" 당부 - 동일 기관 발표와 동일 방제 권고를 재가공한 기사다.
- [major] duplicate_story: 예산군, 드론 활용 밤나무 병해충 방제 추진 / 예산 밤나무 43.49㏊ 드론 방제 - 같은 지역·면적·해충·기간을 다룬 동일 보도자료 기사다.
- [major] wrong_section: 폭염이 밀어올린 채소값…밥상물가도 '펄펄' 끓는다 - 정책 조치보다 채소 가격과 소비 현장이 중심인 수급 기사다.
- [moderate] wrong_section: 폭염·가뭄에 대구·경북 ‘히트플레이션’ 비상 - 출하장려금 내용은 일부뿐이고 대부분 지역 채소 가격 동향이다.
- [moderate] duplicate_story: 예산군 농산물 가격안정 지원사업 관련 2건 - 수급 4번과 정책 7번이 같은 예산군 사업을 반복한다.

### Improvement Hints
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
