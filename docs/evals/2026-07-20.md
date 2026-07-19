## Daily Eval (2026-07-20)
- Overall: **70.99** (warn)
- Operational: **85.73**
- Reader quality: **77.93** (capped; penalty=7.8, cap=90.0, reasons=pest_theme_duplicate, preferred_slot_underfill)
- Quality gate: **70.99** (needs_iteration, editorial_major_issue; editorial=80.2, operational=85.7)
- Scores: completeness=92.8, diversity=94.2, source=71.1, summary=100.0, freshness=40.0, retrieval=89.4, section_fit=100.0, core=100.0, commodity=88.0
- Briefing cards: 18 / Commodity cards: 62
- Sections: supply:5/5 raw=335, policy:5/5 raw=191, dist:5/5 raw=111, pest:3/5 raw=34
- Metrics: title_unique=1.00, domain_diversity=0.78, low_tier=0.22, summary_presence=1.00, summary_numeric=0.67, fresh_72h=0.44, fit_avg=5.39, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=13, commodity_active_today=18, commodity_active_today_unlinked=5, commodity_coverage=0.39, commodity_strict_link=0.92, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.85, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **80.25** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 81.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=4, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 97.5 (minimum_fallback)
- Components: article_selection=78.0, section_fit=83.0, core=84.0, summary=86.0, missed=72.0, noise=78.0
- Summary: 유통(dist)은 핵심 의제가 잘 잡혔지만, 정책(policy)은 농식품부 하반기 업무보고 중복이 과하고, 병해충(pest)은 원자료가 충분한데도 3건만 채우며 현장성 있는 해충·방제 후보를 놓쳤다. 공급(supply)은 주요 가격·작황 기사는 괜찮으나 지역 판촉성 복숭아 기사와 크롤링 잡음이 섞여 일일 브리핑 완성도를 낮춘다.
- [major] bad_summary: 채소값 내렸다는데 오이·상추는 '껑충' - 요약에 기자명, 구독 문구, UI 문구가 그대로 들어가 기사 핵심을 읽기 어렵다.
- [moderate] promotional_filler: 음성군, 장애인 건강소득 지원사업 및 '햇사레 복숭아 ' 출하 성수기 맞... - 지역 판로 홍보와 복지사업이 섞인 약한 로컬 홍보성 기사다.
- [major] duplicate_theme: 농식품부, 'AI 가격 비교 앱' 시범 출시…공공동물병원 도입 추진 - 정책 섹션 5건 중 다수가 같은 농식품부 하반기 업무보고를 반복한다.
- [moderate] missed_candidate: 농지 4필지 중 1필지 위반 의심…마트 가격비교 앱·동물병원 진료비 공... - 농지 전수조사 27.6% 위반 의심은 업무보고 내에서도 독립 의제성이 큰 후보였다.
- [major] underfill: pest section underfilled - 병해충 후보가 34건인데 3건만 선택해 목표 5건을 채우지 못했다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 최신성 점수가 내려갔습니다. 동일 이벤트 중 최신 기사 우선, 96시간 초과 기사 감점을 더 강하게 주는 편이 안정적입니다.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 오래된 기사일수록 배경 설명은 줄이고 이번 보고일 기준으로 새롭게 확인된 조치나 수급 신호를 먼저 적는다.
