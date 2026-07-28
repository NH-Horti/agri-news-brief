## Daily Eval (2026-07-28)
- Overall: **89.45** (pass)
- Operational: **94.63**
- Reader quality: **89.95** (clear; penalty=4.7, cap=100.0, reasons=clear)
- Quality gate: **89.45** (needs_minor_iteration, editorial_acceptance_gate_failed; editorial=86.2, operational=94.6)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=88.8, section_fit=100.0, core=74.6, commodity=98.1
- Briefing cards: 20 / Commodity cards: 41
- Sections: supply:5/5 raw=179, policy:5/5 raw=111, dist:5/5 raw=65, pest:5/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.52, false_positive=0.00, hard_reader_issues=0, weak_core=0.20, editorial_penalty=2.6, commodity_weak=0.00, commodity_items=12, commodity_active_today=16, commodity_active_today_unlinked=4, commodity_coverage=0.36, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.15** (daily target 88, tier=needs_iteration, needs_minor_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 86.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, all_components_min, operational_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=86.0, section_fit=91.0, core=87.0, summary=89.0, missed=79.0, noise=84.0
- Summary: 섹션별 5건을 모두 채웠고 수급·병해충의 현장성 및 유통 핵심 기사 구성은 양호하다. 다만 정책 섹션 후반부가 지역 교육·지원 묶음 기사로 약하며, 원자료에 있는 전국 단위 상생 프로젝트와 제주 유통 컨트롤타워 논의를 놓쳤다. 유통에서도 단순 APC 점검보다 실제 수출 선적 기사가 우선돼야 한다. 전반적으로 사용 가능하지만 후보 우선순위 조정이 필요하다.
- [moderate] missed_candidate: 농식품부, '모두의 상생' 출범…농업·기업 함께 키운다 - 생산·제품화·판로·수출을 포괄하는 전국 단위 신규 사업으로 지역 교육 기사보다 정책성이 높다.
- [moderate] missed_candidate: 제주 농정 '유통 혁신'에 방점…위성곤 도지사 "건의 수용 여부 반드시... - 생산·물류·수급을 총괄할 전담기구 검토는 구체적인 제도 변화로 논산 지역 지원 기사보다 중요하다.
- [moderate] promotional_filler: 예산군, 멜론 수정·시설원예 토양관리·농기계 교육으로 농가 경쟁력 ... - 서로 다른 교육·신청 사업을 묶은 지역 행정 홍보물로 당일 정책 브리핑의 영향도가 낮다.
- [minor] promotional_filler: 논산시, 친환경 먹거리 지원·딸기 우량묘 생산 기반 강화 - 임산부 지원과 딸기 육묘를 한 카드에 합쳐 정책 초점이 분산되고 지역 홍보 성격이 강하다.
- [moderate] missed_candidate: 옥천 명품 복숭아, 홍콩 수출길 올라…올해 10t 수출 목표 - 실제 선적량과 연간 목표가 있는 수출 실행 기사로 단순 APC 방문·점검보다 유통 가치가 높다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=20%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
