## Daily Eval (2026-07-09)
- Overall: **95.17** (pass)
- Operational: **96.67**
- Reader quality: **96.49** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **95.17** (needs_iteration, editorial_acceptance_gate_failed; editorial=82.7, operational=96.7)
- Scores: completeness=100.0, diversity=96.4, source=100.0, summary=97.0, freshness=100.0, retrieval=90.0, section_fit=100.0, core=82.0, commodity=99.1
- Briefing cards: 20 / Commodity cards: 11
- Sections: supply:5/5 raw=180, policy:5/5 raw=138, dist:5/5 raw=59, pest:5/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.65, low_tier=0.15, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=4.48, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=8, commodity_active_today=11, commodity_active_today_unlinked=3, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.70** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 84.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=87.0, core=85.0, summary=77.0, missed=78.0, noise=84.0
- Summary: 전체 4개 섹션 5건씩 채운 점과 주요 수급·물가·도매시장·병해충 이슈를 대체로 포착한 점은 좋다. 다만 정책과 유통에서 더 강한 후보가 보이는데도 사진/행사성·지역 협약성 카드가 들어갔고, 병해충 섹션도 최신 named disease 경보를 일부 놓쳤다. 핵심 카드는 대체로 무난하지만 일부 요약에 크롤링 잔재와 문장 절단이 있어 독자 유용성이 떨어진다.
- [moderate] missed_candidate: 농산물 가격 하락분 지원… 가격안정제 도입 - 가격안정제 시행 시점과 농가 소득 보장 내용을 담은 강한 정책 후보가 있었는데 미선정됐다.
- [moderate] noise: 자식처럼 키운 농산물 제값 찾고 싶은 농민들[금주의 B컷] - 사진/칼럼 성격이 강하고 같은 가격 폭락 테마를 반복해 정책 브리핑 가치가 낮다.
- [moderate] promotional_filler: 합천유통· 사과 대추 공선 출하 회, 공동 출하 협약 …"시장 경쟁력 높여" - 지역 공동출하 협약 홍보에 가까워 전국 유통·물류 독자에게 우선순위가 낮다.
- [moderate] missed_candidate: 강호동 농협 회장, 강서공판장 찾아 농산물 수급 점검 - 반입 물량·경매가격·출하 조절을 다룬 구체적 시장운영 후보가 미선정됐다.
- [moderate] missed_candidate: 화순군, '잦은 비·고습도'에 병해충 비상... 벼 재배지 예찰 강화 요청 - 도열병·잎집무늬마름병·흰잎마름병 등 named disease 위험을 다룬 현재성 있는 후보가 빠졌다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
