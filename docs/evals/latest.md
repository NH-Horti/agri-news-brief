## Daily Eval (2026-07-09)
- Overall: **93.59** (pass)
- Operational: **97.06**
- Reader quality: **96.70** (clear; penalty=0.4, cap=100.0, reasons=clear)
- Quality gate: **93.59** (needs_iteration, editorial_major_issue; editorial=80.5, operational=97.1)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=100.0, freshness=100.0, retrieval=90.0, section_fit=100.0, core=83.1, commodity=99.1
- Briefing cards: 20 / Commodity cards: 14
- Sections: supply:5/5 raw=222, policy:5/5 raw=190, dist:5/5 raw=68, pest:5/5 raw=39
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.20, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.83, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.2, commodity_weak=0.00, commodity_items=8, commodity_active_today=12, commodity_active_today_unlinked=4, commodity_coverage=0.24, commodity_strict_link=0.88, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **80.55** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 81.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=85.0, core=80.0, summary=78.0, missed=76.0, noise=82.0
- Summary: 전 섹션 5건을 채운 점과 가격 폭락 대응, 과일 관측, 가락시장 휴업, 온라인도매 물류혁신, 과수화상병 예찰 등 핵심 이슈 포착은 양호하다. 다만 정책은 물가·가격안정제 테마가 과밀하고, 유통·병해충 섹션에는 더 구체적인 운영·해충 리스크 후보가 있는데도 지역 협약·일반 생육관리성 기사가 들어갔다. 일부 요약은 원문 찌꺼기와 문장 깨짐이 있어 독자 효용을 떨어뜨린다.
- [moderate] promotional_filler: [농가월령가] 충남 멜론 의 미래 품종 다변화와 프리미엄 전략에 달렸다 - 칼럼·전략성 지역 품목 홍보에 가까워 당일 수급·가격 브리핑 가치가 낮다.
- [moderate] duplicate_theme: 농산물 가격 하락분 지원… 가격안정제 도 입 - 앞선 가격 폭락·정부 총력 대응 기사와 가격안정제·경영안정망 내용이 크게 겹친다.
- [moderate] bad_summary: "취약계층, 농식품 물가 상승 직격탄 맞아" - 요약에 '생활 필 일률적...'처럼 원문 조각이 섞여 문장이 깨졌다.
- [moderate] promotional_filler: 합천유통· 사과 대추 공선 출하 회, 공동 출하 협약 …"시장 경쟁력 높여" - 지역 공선출하 협약성 기사로 전국 유통·물류 독자에게는 구체 운영 정보가 약하다.
- [moderate] missed_candidate: 농협경제지주, 농산물 유통사업 발전 협업그룹 발대 - 산지·도매·소매 정보 공유와 수급상황 연계라는 구체 유통 운영 후보가 빠졌다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
