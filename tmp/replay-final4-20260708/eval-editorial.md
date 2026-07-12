## Daily Eval (2026-07-08)
- Overall: **93.23** (pass)
- Operational: **95.20**
- Reader quality: **95.02** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **93.23** (needs_iteration, editorial_acceptance_gate_failed; editorial=80.8, operational=95.2)
- Scores: completeness=100.0, diversity=85.3, source=80.0, summary=97.0, freshness=100.0, retrieval=89.4, section_fit=100.0, core=92.0, commodity=96.8
- Briefing cards: 20 / Commodity cards: 17
- Sections: supply:5/5 raw=195, policy:5/5 raw=143, dist:5/5 raw=90, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.55, low_tier=0.20, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=4.63, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=9, commodity_active_today=11, commodity_active_today_unlinked=2, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.56, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **80.85** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 81.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=86.0, core=79.0, summary=76.0, missed=77.0, noise=82.0
- Summary: 전 섹션 5건을 채운 점과 배추 약세, 가격안정제, 제주 항공물류, 과수화상병·고추 탄저병 등 핵심 이슈를 잡은 점은 좋다. 다만 공급·유통에서 더 강한 주산지 르포와 APC/공동출하 후보가 보였는데도 지역 행사성·PR성 기사와 약한 코어가 섞였고, 정책은 같은 정부 가격안정 대책을 반복했다. 일부 요약은 본문 대신 캡션·스크랩 문구가 남아 독자 효용을 낮춘다.
- [moderate] missed_candidate: [주산지 르포] 얼갈이배추·오이 경락값 5년만에 최저…“안전장치 시급...” - 오이·애호박 가격 폭락의 현장성과 가격 신호가 강한 후보였지만 집회 판매전·사설성 기사에 밀렸다.
- [moderate] weak_core: 햇 마늘 가격 지지 힘쏟는다 - 창녕농협 초매식·APC 운영 중심의 지역성 기사라 공급 코어로는 약하다.
- [moderate] bad_summary: 햇 마늘 가격 지지 힘쏟는다 - 요약이 제목·캡션을 그대로 끌어와 핵심 수치와 가격 지지 대책을 설명하지 못한다.
- [moderate] duplicate_theme: 농산물 값↓·농자재값↑…정부, 농가 경영부담 완화에 총력 - 가격안정제 시행 기사와 같은 농식품부 대책을 반복해 정책 슬롯의 의제 폭을 좁힌다.
- [moderate] missed_candidate: 영동 학산농협, 공동선별·분산출하로 블루베리 경쟁력 높인다 - APC 기반 공동선별·분산출하라는 구체적 유통 운영 기사인데 지역 계약재배·초매식 기사보다 우선되지 않았다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
