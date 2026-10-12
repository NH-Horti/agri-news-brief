## Daily Eval (2026-10-13)
- Overall: **91.64** (warn)
- Operational: **92.86**
- Reader quality: **92.14** (clear; penalty=0.7, cap=100.0, reasons=clear)
- Quality gate: **91.64** (needs_iteration, editorial_acceptance_gate_failed; editorial=82.6, operational=92.9)
- Scores: completeness=100.0, diversity=92.4, source=80.0, summary=100.0, freshness=100.0, retrieval=69.0, section_fit=97.2, core=72.7, commodity=87.0
- Briefing cards: 20 / Commodity cards: 30
- Sections: supply:5/5 raw=276, policy:5/5 raw=43, dist:5/5 raw=66, pest:5/5 raw=9
- Metrics: title_unique=1.00, domain_diversity=0.65, low_tier=0.20, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.42, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=6, commodity_active_today=12, commodity_active_today_unlinked=6, commodity_coverage=0.18, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.83, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.60** (daily target 82, tier=daily_pass, needs_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 82.60; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=88.0, core=89.0, summary=92.0, missed=70.0, noise=68.0
- Summary: 정량 목표와 핵심 기사 구성은 충족했지만, 유통 부문에 동일 업체 교육 기사 2건과 지역 판촉 행사가 포함돼 강한 운영·채널 후보를 놓쳤다. 병해충의 지역의회 기사도 현장성이 약하다.
- [moderate] duplicate_theme: 동화청과 교육 기사 2건 - 같은 업체의 출하교육 두 건이 유통 섹션을 중복 점유한다.
- [moderate] missed_candidate: aT, 농수산물 온라인도매시장 판매자 참여 문턱 낮춘다 - 판매자 가입요건 폐지는 전국 유통채널 운영 변화로 교육 기사보다 중요하다.
- [moderate] promotional_filler: 천원 사과·천원택배…이번 주말 '충주씨 농산물 직거래한마당' - 일회성 지역 행사·할인 홍보 성격이 강하다.
- [moderate] missed_candidate: 농협, 한국산 배 브랜드 경쟁력 강화 - 수출용 표준 패키지는 구체적인 판매·브랜드 운영 변화다.
- [moderate] noise: 예산군의회 임시회 개회…벼 공동 방제·농업 배수로 정비 촉구 - 방제 요구가 임시회 종합 기사에 묻혀 구체적 위험·대응 정보가 부족하다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: policy, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=20%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
