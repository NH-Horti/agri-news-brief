## Daily Eval (2026-07-28)
- Overall: **83.68** (warn)
- Operational: **93.35**
- Reader quality: **85.07** (clear; penalty=8.3, cap=100.0, reasons=clear)
- Quality gate: **83.68** (needs_iteration, editorial_acceptance_gate_failed; editorial=82.5, operational=93.3)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=88.8, section_fit=100.0, core=84.8, commodity=98.1
- Briefing cards: 20 / Commodity cards: 41
- Sections: supply:5/5 raw=177, policy:5/5 raw=112, dist:5/5 raw=65, pest:5/5 raw=52
- Metrics: title_unique=1.00, domain_diversity=0.80, low_tier=0.15, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=3.64, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=4.6, commodity_weak=0.00, commodity_items=12, commodity_active_today=16, commodity_active_today_unlinked=4, commodity_coverage=0.36, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.45** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 82.50; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, operational_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=85.0, core=77.0, summary=92.0, missed=76.0, noise=81.0
- Summary: 섹션별 5건을 채웠고 공급 기사와 요약 품질은 안정적이다. 다만 정책에 지역 가공공장·정부 홍보성 할인 기사가 들어갔고, 유통에서는 구체적인 수출 실적을 놓쳤다. 병해충은 과수화상병과 실제 혹명나방 피해보다 일반 당부·교육 기사를 핵심으로 잡아 코어 우선순위 조정이 필요하다.
- [moderate] wrong_section: 완도 고금도 최첨단 유자 가공공장 구축…10월 착공 - 민간 가공·수매·수출 인프라 투자로 정책보다 유통·가공 섹션에 가깝다.
- [moderate] promotional_filler: 복날에 지갑 열자 '정부 30% 할인'으로 삼계탕 물가 방어하는 법 - 정부 기자단식 소비 안내 성격이 강하고 정책의 규모·대상·효과 설명이 약하다.
- [moderate] weak_core: 충북농협, 영동농협 APC 찾아 포도 출하 준비·안전관리 점검 - 단순 현장 점검 기사여서 유통개혁·온라인도매시장 기사와 같은 코어 등급은 과하다.
- [moderate] missed_candidate: 옥천 명품 복숭아, 홍콩 수출길 올라…올해 10t 수출 목표 - 실제 선적량과 연간 목표가 있는 구체적 수출·판로 기사인데 현장 점검·기술 기사보다 우선도가 높다.
- [moderate] weak_core: 과수화상병 '미리바 스프레이'로 진단 가능 - 발생면적 10.9% 증가와 현장 진단 수단을 함께 다뤄 일반 방제 당부보다 중요하다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=30%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
