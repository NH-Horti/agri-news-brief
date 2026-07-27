## Daily Eval (2026-07-28)
- Overall: **90.26** (pass)
- Operational: **93.55**
- Reader quality: **90.97** (clear; penalty=2.6, cap=100.0, reasons=clear)
- Quality gate: **90.26** (needs_minor_iteration, editorial_acceptance_gate_failed; editorial=85.2, operational=93.5)
- Scores: completeness=100.0, diversity=92.0, source=60.0, summary=100.0, freshness=100.0, retrieval=88.8, section_fit=100.0, core=72.6, commodity=98.1
- Briefing cards: 20 / Commodity cards: 41
- Sections: supply:5/5 raw=177, policy:5/5 raw=112, dist:5/5 raw=66, pest:5/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.25, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=3.54, false_positive=0.00, hard_reader_issues=0, weak_core=0.22, editorial_penalty=0.6, commodity_weak=0.00, commodity_items=12, commodity_active_today=16, commodity_active_today_unlinked=4, commodity_coverage=0.36, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **85.15** (daily target 88, tier=needs_iteration, needs_minor_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 85.20; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, operational_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=87.0, section_fit=86.0, core=81.0, summary=92.0, missed=78.0, noise=88.0
- Summary: 20개 슬롯을 모두 채웠고 수급·유통·병해충의 현장성 및 요약 품질은 전반적으로 좋다. 다만 정책 섹션의 핵심 기사 선정과 섹션 정합성이 약하고, 유통에서는 전국 단위 판로 사업을 두고 지역 점검성 기사를 택했다. 병해충도 과수화상병보다 유사한 탄저병 경보를 핵심으로 앞세운 점이 아쉽다.
- [moderate] wrong_section: 마트마다 다른 농축산물값…AI가 ‘싼 곳’ 찾아준다 [D:로그인] - 구체적인 농정 조치보다 소비자 가격비교 기술을 소개한 기획물로, 정책 핵심 카드로는 약하다.
- [moderate] wrong_section: 점점 악화하는 가뭄에 농작물 관리 초비상 - 제주 가뭄과 생육 위험이 중심이며 정책 대응 내용은 부차적이어서 수급 섹션에 더 가깝다.
- [moderate] missed_candidate: 제주 농정 '유통 혁신'에 방점…위성곤 도지사 "건의 수용 여부 반드시... - 생산·물류·수급을 총괄하는 전담기구 검토와 정책협의체 구성이 선별된 지역 시범사업보다 구체적이다.
- [moderate] missed_candidate: 현대그린푸드·CJ제일제당·오리온이 농가와 한 팀…제품·수출까지 ‘... - 계약재배부터 제품화·판로·수출까지 연결하는 전국 단위 사업으로 지역 APC 점검보다 파급력이 크다.
- [moderate] weak_core: [리포트] 가격 폭락에 폭염까지.. 고랭지 배추 갈아엎는 농민들 - 출하 포기와 산지 폐기가 확인된 강한 수급 신호인데 비핵심으로 배치됐다.

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
