## Daily Eval (2026-07-08)
- Overall: **94.96** (pass)
- Operational: **96.29**
- Reader quality: **96.11** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **94.96** (needs_iteration, editorial_acceptance_gate_failed; editorial=83.4, operational=96.3)
- Scores: completeness=100.0, diversity=88.9, source=80.0, summary=97.0, freshness=100.0, retrieval=89.4, section_fit=100.0, core=98.4, commodity=96.8
- Briefing cards: 20 / Commodity cards: 17
- Sections: supply:5/5 raw=195, policy:5/5 raw=143, dist:5/5 raw=90, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.20, summary_presence=1.00, summary_numeric=0.65, fresh_72h=1.00, fit_avg=4.41, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=9, commodity_active_today=12, commodity_active_today_unlinked=3, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.56, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.40** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 85.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=86.0, section_fit=88.0, core=83.0, summary=76.0, missed=82.0, noise=84.0
- Summary: 전 섹션 5건을 채웠고 핵심 이슈인 채소 가격 약세, 가격안정제, 제주 항공물류, 과수화상병 대응은 잘 잡았다. 다만 공급·정책에서 가격 폭락 테마가 과밀하고, 일부 코어가 지역성 기사에 머물며, 원문 긁힘형 요약이 여러 건 보여 일일 브리핑 완성도는 88점권에는 못 미친다.
- [moderate] bad_summary: [주산지 르포] 얼갈이배추·오이 경락값 5년만에 최저…“안전장치 시급... - 제목과 본문 조각이 반복되고 문장이 중간에 끊겨 독자가 핵심 수치를 파악하기 어렵다.
- [moderate] bad_summary: 반복되는 채소 산지폐기, 이제 끝내야 - 요약이 중복·절단된 스크랩 형태이며 논설 기사 성격도 드러나지 않는다.
- [moderate] missed_candidate: [주산지 르포] 벼랑 끝 내몰린 농가…“양배추 수확할수록 손해” - 현장성·신선도·품목성이 높은 양배추 르포가 논설성 산지폐기 기사보다 브리핑 가치가 크다.
- [moderate] weak_core: 햇 마늘 가격 지지 힘쏟는다 - 창녕농협 초매식 중심의 지역 산지 기사로 전국 공급 코어로는 약하다.
- [moderate] missed_candidate: 강달러·고임금에 ‘허덕’ 농산물은 ‘헐값’...시름 깊은 농업 - 고환율·생산비·저가격을 묶은 구조적 정책 기사인데 농림위성·농협 점검성 기사보다 당일 농정 맥락이 강하다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
