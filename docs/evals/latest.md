## Daily Eval (2026-07-23)
- Overall: **76.00** (warn)
- Operational: **96.77**
- Reader quality: **84.00** (capped; penalty=6.5, cap=84.0, reasons=pest_theme_duplicate, commodity_false_link, commodity_false_link_severe)
- Quality gate: **76.00** (needs_major_iteration, editorial_major_issue; editorial=75.2, operational=96.8)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=95.5, freshness=100.0, retrieval=87.5, section_fit=95.8, core=93.3, commodity=97.2
- Briefing cards: 20 / Commodity cards: 22
- Sections: supply:5/5 raw=161, policy:5/5 raw=87, dist:5/5 raw=67, pest:5/5 raw=49
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.15, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=3.54, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=10, commodity_active_today=13, commodity_active_today_unlinked=3, commodity_coverage=0.30, commodity_strict_link=0.80, commodity_false_link=0.10, commodity_pool_false_link=0.00, commodity_dominant_section=0.40, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **75.15** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 75.40; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=6, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=78.0, section_fit=76.0, core=73.0, summary=80.0, missed=67.0, noise=76.0
- Summary: 분량과 신선도는 좋지만, 핵심 선별에서 강한 가격·수급 위기 기사와 전국 단위 유통 기사를 놓치고 일부 지역 의회·기업 지원·농가 프로필성 기사가 자리를 차지했다. 특히 dist 섹션은 정책성·프로필성 기사 혼입이 커서 섹션 정체성이 약하다. pest는 주요 병해충 대응 흐름은 잡았으나 제품 홍보성 기사와 부실 요약이 품질을 낮췄다.
- [major] missed_candidate: “샛별 보고 농사짓는데 3년째 빚만 는다”…배추값 폭락에 수확 대신 산지 폐기 - 배추 가격 폭락과 산지폐기라는 당일 핵심 수급 이슈가 빠지고 낮은 영향도의 지원·품종 기사가 포함됐다.
- [moderate] weak_core: 복숭아 포장자재 지원 수급 안정 도모 - 수급 안정 관련성은 있으나 자재 지원 사업 중심이라 당일 코어로는 영향력이 약하다.
- [moderate] promotional_filler: 서울청과, ' 산지 맞춤형 자재 지원'으로 농가 상생 강화 - 민간 도매법인의 상생 지원 홍보에 가까워 정책 섹션 기사로 약하다.
- [major] missed_candidate: 제주도, 장바구니 10개 품목 상시 추적… 위기 땐 긴급재정 투입 - 생활물가·농산물 수급을 상시 점검하고 재정 투입까지 다루는 강한 정책 후보가 누락됐다.
- [major] wrong_section: 이경재 경남도의원 "저품위 마늘 피해 농가 소외돼선 안 돼" - 저품위 마늘 지원 대상 확대 촉구로 정책·지원 이슈이지 유통·물류 운영 기사가 아니다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
