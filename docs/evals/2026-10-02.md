## Daily Eval (2026-10-02)
- Overall: **85.47** (warn)
- Operational: **93.65**
- Reader quality: **93.47** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **85.47** (needs_major_iteration, editorial_major_issue; editorial=62.6, operational=93.7)
- Scores: completeness=100.0, diversity=84.6, source=80.0, summary=100.0, freshness=100.0, retrieval=80.5, section_fit=100.0, core=81.1, commodity=88.0
- Briefing cards: 20 / Commodity cards: 16
- Sections: supply:5/5 raw=194, policy:5/5 raw=51, dist:5/5 raw=29, pest:5/5 raw=21
- Metrics: title_unique=1.00, domain_diversity=0.55, low_tier=0.20, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=3.53, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=5, commodity_active_today=10, commodity_active_today_unlinked=5, commodity_coverage=0.15, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=1.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **62.65** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 63.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=4, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, commodity_board_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=62.0, section_fit=78.0, core=55.0, summary=88.0, missed=45.0, noise=45.0
- Summary: 형식과 요약은 양호하지만 공급 섹션의 심각한 기사 중복, 약한 코어 지정, 유통 핵심 후보 누락으로 편집 품질이 크게 떨어진다.
- [major] duplicate_story: "사과·배는 싸졌는데"…비 자주 오더니 채소값 줄줄이 올랐다 외 2건 - 공급 5건 중 4건이 같은 9월 품목별 물가 흐름을 반복한다.
- [major] missed_candidate: 가을에도 밭 갈아엎는다…‘양배추’ 농가에 무슨 일이? - 연속 시장격리와 산지가격 하락을 다룬 당일 핵심 수급 기사다.
- [moderate] wrong_section: 도, 가을철 농산물 판로 확대 추진… 가격하락 대응 - 내용의 중심이 판로 확대와 유통망 다변화여서 유통 섹션에 더 적합하다.
- [moderate] weak_core: 김제 농협, 두류산업 선도 농협 ‘자리매김’…농가실익 보탬 - 개별 농협 성과 소개 성격이 강해 전국 정책 코어로는 약하다.
- [moderate] missed_candidate: '법정위원회'로 도약한 농산물 수급조절위, 제8기 출범 - 법정위원회 전환은 수급정책 의사결정 구조의 실질적 변화다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 품목 보드 대표 품목 수가 적습니다. 다만 weak fallback으로 채우지 말고, 품목명+이슈가 제목에 함께 드러나는 후보를 리콜 쿼리에서 보강하세요.
- 리콜 시드 결손이 보입니다: policy. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
