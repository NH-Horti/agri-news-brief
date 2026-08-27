## Daily Eval (2026-08-28)
- Overall: **90.05** (pass)
- Operational: **94.28**
- Reader quality: **92.60** (clear; penalty=1.7, cap=100.0, reasons=clear)
- Quality gate: **90.05** (needs_major_iteration, editorial_major_issue; editorial=76.8, operational=94.3)
- Scores: completeness=100.0, diversity=92.0, source=60.0, summary=100.0, freshness=100.0, retrieval=91.2, section_fit=95.2, core=87.0, commodity=90.0
- Briefing cards: 20 / Commodity cards: 30
- Sections: supply:5/5 raw=313, policy:5/5 raw=72, dist:5/5 raw=78, pest:5/5 raw=30
- Metrics: title_unique=1.00, domain_diversity=0.80, low_tier=0.25, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=2.81, false_positive=0.00, hard_reader_issues=0, weak_core=0.17, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=7, commodity_active_today=15, commodity_active_today_unlinked=8, commodity_coverage=0.21, commodity_strict_link=0.86, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.71, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **76.80** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 77.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=76.0, section_fit=74.0, core=79.0, summary=91.0, missed=67.0, noise=72.0
- Summary: 형식과 기사 수, 요약은 좋지만 정책의 CPTPP 3중 반복, 공급의 해외 기후 잡음, 유통의 지역 수출 행사성 꼬리, 병해충의 약한 현장점검 선택이 편집 밀도를 떨어뜨린다.
- [major] duplicate_theme: CPTPP 가입 관련 기사 3건 - 농식품부 입장·여야 반응·논의 착수가 같은 현안을 반복해 정책 지면 60%를 차지한다.
- [moderate] missed_candidate: '농망법'일까 '희망법'일까…양곡·농안법, 수급관리 시험대 - 당일 시행된 양곡관리법·농안법의 작동 방식과 쟁점을 다룬 핵심 정책 기사다.
- [moderate] wrong_section: 폭염·가뭄에 시름하는 대곡 단감 농가 - 일소·고사 등 기상 기반 생육 피해가 중심이므로 pest의 성장위험 범주에 더 적합하다.
- [moderate] noise: 벨기에 감자는 ‘탁구공’ 크기, 프랑스선 악어 자연부화… - 국내 농업 독자와의 연관성이 약하고 악어 부화 대목까지 섞인 해외 화제성 기사다.
- [moderate] promotional_filler: 장성군, 샤인머스캣 4톤 대만 첫 수출 - 4톤 첫 수출과 상차식 중심의 지역 홍보성 기사로 운영상 파급력이 제한적이다.

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
