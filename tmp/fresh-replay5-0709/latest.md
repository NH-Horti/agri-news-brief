## Daily Eval (2026-07-09)
- Overall: **92.70** (pass)
- Operational: **94.89**
- Reader quality: **93.20** (capped; penalty=1.7, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **92.70** (needs_minor_iteration, editorial_acceptance_gate_failed; editorial=87.2, operational=94.9)
- Scores: completeness=96.4, diversity=90.7, source=96.8, summary=100.0, freshness=100.0, retrieval=90.0, section_fit=100.0, core=92.6, commodity=96.1
- Briefing cards: 19 / Commodity cards: 12
- Sections: supply:5/5 raw=180, policy:5/5 raw=138, dist:5/5 raw=59, pest:4/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.58, low_tier=0.16, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=4.72, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=7, commodity_active_today=11, commodity_active_today_unlinked=4, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **87.20** (daily target 88, tier=needs_iteration, needs_minor_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 87.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, operational_score_min, no_section_underfill)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=88.0, section_fit=90.0, core=87.0, summary=86.0, missed=84.0, noise=88.0
- Summary: 전반적으로 수급·정책·유통의 핵심 이슈는 잘 잡았고, 온라인도매시장 물류·먹거리 물가 점검·과일 관측 등 독자 효용이 높은 카드가 포함됐다. 다만 pest가 4건으로 underfill됐고, 일부 섹션에서 가격 폭락 테마가 반복되며, dist와 pest의 후순위 카드에 지역 행사·일반 안내성 기사가 섞였다. 핵심 선정은 대체로 양호하지만 pest core와 일부 요약 품질은 개선 여지가 있다.
- [moderate] underfill: pest 섹션 4건 편성 - 원자료에 화순 벼 병해충, 장수 장마철 방제 등 비중복 후보가 있었는데 5건 목표를 채우지 못했다.
- [moderate] missed_candidate: 화순군, '잦은 비·고습도'에 병해충 비상... 벼 재배지 예찰 강화 요청 - 도열병·잎집무늬마름병·흰잎마름병 등 구체 병해 리스크가 있어 underfill 보완 후보로 적합했다.
- [moderate] weak_core: 농사포인트 - 사과 갈색무늬병 16~28℃ 수분존재 시간 길어질수록 발생... - 유용한 재배 정보지만 기사성이 약한 종합 안내 칼럼이라 core로는 다소 약하다.
- [moderate] promotional_filler: 합천유통· 사과 대추 공선 출하 회, 공동 출하 협약 …"시장 경쟁력 높여" - 지역 단위 협약식 성격이 강하고 전국 유통·물류 운영 영향이 제한적이다.
- [moderate] duplicate_theme: 농산물 가격 폭락에 농민 울분…정부, 경영 안정 위해 '총력 대응' - supply의 농민대회 카드와 policy의 가격안정제 카드까지 가격 폭락·대책 테마가 반복된다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
