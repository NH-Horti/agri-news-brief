## Daily Eval (2026-09-28)
- Overall: **73.22** (warn)
- Operational: **83.06**
- Reader quality: **74.56** (capped; penalty=8.5, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **73.22** (needs_major_iteration, editorial_acceptance_gate_failed; editorial=76.7, operational=83.1)
- Scores: completeness=100.0, diversity=96.4, source=100.0, summary=100.0, freshness=25.0, retrieval=90.0, section_fit=100.0, core=85.0, commodity=71.0
- Briefing cards: 20 / Commodity cards: 41
- Sections: supply:5/5 raw=347, policy:5/5 raw=204, dist:5/5 raw=65, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.65, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=0.35, fit_avg=4.38, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.5, commodity_weak=0.00, commodity_items=10, commodity_active_today=20, commodity_active_today_unlinked=10, commodity_coverage=0.30, commodity_strict_link=0.70, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.80, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **76.65** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 77.10; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min, operational_score_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=77.0, section_fit=73.0, core=72.0, summary=90.0, missed=73.0, noise=76.0
- Summary: 20건을 모두 채우고 요약도 유용하지만, 공급 섹션에 유통·정책 기사가 섞였고 해충 섹션의 핵심 선정과 꼬리 기사 품질이 약하다. 유통에서는 더 강한 전국 단위 운영 후보를 놓쳤다.
- [moderate] wrong_section: 가락시장 파렛트 출하 의무화 확대…느타리버섯·봄동·제주당근 대상 - 출하 물류와 도매시장 운영을 다룬 전형적인 유통 기사다.
- [moderate] wrong_section: 예산군, 농산물 가격 하락 농가에 가격 안정기금 지원 - 지자체 가격안정 지원제도여서 공급보다 정책 성격이 강하다.
- [moderate] weak_core: 옥천군농업기술센터, 포도 수확 후 "병해충 방제 ·충분한 물주기" 당부 - 지역 농가 대상의 일반 관리 안내로 핵심 뉴스성이 부족하므로 core에서 demote해야 한다.
- [moderate] promotional_filler: 강대현·송양숙 부부(순천원예농협 대의원) - 꼼꼼한 영농일지 기록과 ... - 농가 인물 소개가 중심이며 구체적인 병해충 위험이나 대응 동향이 약하다.
- [moderate] missed_candidate: 농협경제지주, 전속출하 중심 유통개혁 추진…도농 직거래망도 확대 - 전국 단위 출하체계와 직거래망 개편으로 AI 선별 사례보다 운영 파급력이 크다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 최신성 점수가 내려갔습니다. 동일 이벤트 중 최신 기사 우선, 96시간 초과 기사 감점을 더 강하게 주는 편이 안정적입니다.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 오래된 기사일수록 배경 설명은 줄이고 이번 보고일 기준으로 새롭게 확인된 조치나 수급 신호를 먼저 적는다.
