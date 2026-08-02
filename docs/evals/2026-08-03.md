## Daily Eval (2026-08-03)
- Overall: **51.90** (fail)
- Operational: **89.95**
- Reader quality: **86.35** (clear; penalty=3.6, cap=100.0, reasons=clear)
- Quality gate: **51.90** (needs_major_iteration, editorial_blocking_issue; editorial=51.9, operational=90.0)
- Scores: completeness=100.0, diversity=88.0, source=40.0, summary=100.0, freshness=95.7, retrieval=78.3, section_fit=98.6, core=80.6, commodity=91.4
- Briefing cards: 20 / Commodity cards: 34
- Sections: supply:5/5 raw=348, policy:5/5 raw=144, dist:5/5 raw=72, pest:5/5 raw=16
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.30, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=4.11, false_positive=0.00, hard_reader_issues=0, weak_core=0.29, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=11, commodity_active_today=17, commodity_active_today_unlinked=6, commodity_coverage=0.33, commodity_strict_link=0.82, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.64, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **51.90** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 51.90; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=1, major=3, reasons=editorial_score_min, no_blocking_issues, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=47.0, section_fit=68.0, core=59.0, summary=66.0, missed=35.0, noise=30.0
- Summary: 형식상 섹션별 5건을 채웠지만 실질적인 기사 다양성과 선별 품질이 크게 부족하다. dist는 동일한 경북 스마트 APC 보도를 5건 모두 중복 게재했고, pest도 동일한 경북농기원 발표를 반복한 데다 텃밭 생활정보와 업체 홍보성 기사를 포함했다. policy와 supply 역시 원자료에 있는 더 강한 전국 단위 수급·정책 기사를 놓치고 지역 건의, 논평, 해외 와인 기사 등을 선택했다. 일부 요약은 문장이 잘리거나 기사보다 운영적 의미를 과장해 일일 브리핑으로 수용하기 어렵다.
- [major] duplicate_story: 경북도, AI·로봇 활용 스마트 APC 확대…농산물 유통 'AX' 속도 - dist 5건 전부가 경북도의 동일한 1433억원 스마트 APC 발표를 재보도한 기사다.
- [major] duplicate_story: 폭염·가뭄 이중고에 과수·채소 비상…경북농기원 "수분관리 집중해야... - 1번 카드와 같은 경북농업기술원 폭염·건조 관리 발표를 옮긴 중복 기사이며 둘 다 core다.
- [blocking] off_topic: “심기만 하면 끝?” 초보 텃밭족이 여름마다 후회하는 9가지 실수 - 초보 취미 텃밭 생활정보로서 상업 농업의 병해충 발생·대응 브리핑과 무관하다.
- [moderate] promotional_filler: 20년 넘게 호흡 맞춰 온 아그리젠토 충남지사!! - 농약업체 지역지사와 영업 인력을 소개하는 홍보성 프로필이며 실제 병해충 위험 신호가 아니다.
- [moderate] weak_core: 함양군, 농식품부에 양파 수급 안정·국비사업 지원 건의 - 한 지자체의 지원 요청에 그쳐 전국 정책 실행이나 정부 결정으로 보기 어렵다. core에서 demote해야 한다.

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
