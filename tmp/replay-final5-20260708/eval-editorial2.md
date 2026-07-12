## Daily Eval (2026-07-08)
- Overall: **94.30** (pass)
- Operational: **96.00**
- Reader quality: **95.82** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **94.30** (needs_iteration, editorial_acceptance_gate_failed; editorial=81.9, operational=96.0)
- Scores: completeness=100.0, diversity=85.3, source=80.0, summary=98.5, freshness=100.0, retrieval=89.4, section_fit=100.0, core=100.0, commodity=96.8
- Briefing cards: 20 / Commodity cards: 17
- Sections: supply:5/5 raw=195, policy:5/5 raw=143, dist:5/5 raw=90, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.55, low_tier=0.20, summary_presence=1.00, summary_numeric=0.65, fresh_72h=1.00, fit_avg=4.41, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=9, commodity_active_today=12, commodity_active_today_unlinked=3, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.56, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **81.90** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 82.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=85.0, section_fit=88.0, core=80.0, summary=78.0, missed=77.0, noise=82.0
- Summary: 분량과 신선도는 충족했고 가격 급락·수급안정이라는 당일 핵심 의제도 대체로 잡았다. 다만 공급·정책 섹션은 같은 채소 가격 폭락 테마가 과밀하고, 유통 섹션에는 강호동 현장점검류 약한 반복성 카드가 남았다. 병해충은 과수화상병 전국 동향 카드가 더 핵심인데 고추 탄저병만 core로 둔 점이 아쉽다. 일부 요약은 본문 크롤링 문구가 그대로 남아 독자 효용을 떨어뜨린다.
- [moderate] missed_candidate: [주산지 르포] 벼랑 끝 내몰린 농가…“양배추 수확할수록 손해” - 구체적 현장 르포와 비용·가격 압박이 강한데 사설성 산지폐기 카드가 대신 들어갔다.
- [moderate] bad_summary: [주산지 르포] 얼갈이배추·오이 경락값 5년만에 최저… - 제목과 본문 조각이 반복되고 문장이 끊겨 핵심 수치와 현장 메시지가 잘 전달되지 않는다.
- [moderate] duplicate_theme: 반복되는 채소 산지폐기, 이제 끝내야 - 배추·오이·양배추 가격 폭락 카드가 이미 여러 장인데 이 카드는 사설성 중복이 크다.
- [moderate] missed_candidate: 강달러·고임금에 ‘허덕’ 농산물은 ‘헐값’...시름 깊은 농업 - 고환율·인건비·농산물 저가를 묶은 구조적 정책 이슈가 소비자단체 회의보다 핵심성이 높다.
- [moderate] weak_core: 경북도 "장마철 고추 탄저병 비상, 예방이 최우선!" - 병해충 core가 지역 고추 예방 당부에 머물고, 과수화상병 전국 발생·방제방식 변화 카드가 더 핵심이다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
