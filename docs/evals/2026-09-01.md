## Daily Eval (2026-09-01)
- Overall: **82.68** (warn)
- Operational: **96.30**
- Reader quality: **84.00** (capped; penalty=7.3, cap=84.0, reasons=pest_theme_duplicate, commodity_false_link, commodity_false_link_severe)
- Quality gate: **82.68** (needs_major_iteration, editorial_acceptance_gate_failed; editorial=76.7, operational=96.3)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=90.6, section_fit=87.5, core=85.0, commodity=100.0
- Briefing cards: 20 / Commodity cards: 43
- Sections: supply:5/5 raw=262, policy:5/5 raw=58, dist:5/5 raw=63, pest:5/5 raw=49
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.10, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=3.71, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=7, commodity_active_today=19, commodity_active_today_unlinked=12, commodity_coverage=0.21, commodity_strict_link=0.86, commodity_false_link=0.14, commodity_pool_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **76.70** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 78.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=0, reasons=editorial_score_min, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=78.0, section_fit=80.0, core=70.0, summary=89.0, missed=69.0, noise=75.0
- Summary: 수량과 요약은 안정적이지만 정책 핵심 선정이 약하고, 유통 섹션에 작황 기사가 섞였다. 강한 법·통상 후보를 두고 일반 물가 대담과 정부 해명자료를 중용한 점이 가장 큰 약점이다.
- [moderate] weak_core: [사실은 이렇습니다] 정부는 외식물가 안정을 위해 농산물 가격 안정에 ... - 구체적 신규 조치가 부족한 해명자료로 정책 핵심 기사로는 약하다.
- [moderate] weak_core: 정부, CPTPP 가입 본격화…농민단체 "농업 희생 전제한 개방 중단하라" - 농업 통상과 생산자 영향을 다룬 주요 정책 현안인데 비핵심으로 배치됐다.
- [moderate] missed_candidate: 할당관세 악용 막는다…'반출 지연' 땐 혜택 환수 추진 - 시장 공급 지연과 관세 혜택 환수를 다룬 구체적 제도 변화로 일반 물가 대담보다 강하다.
- [moderate] noise: [생생뉴스] 치솟는 물가에 가계 부담 가중…물가 안정 대책은? - 일반 경제학자 대담 중심이며 농업정책의 구체적 조치나 운영 정보가 부족하다.
- [moderate] wrong_section: "뜨거운 여름 덕분에 오히려 달다" 고당도 나주 햇배 출하 - 유통 운영보다 생산량·작황·품질을 중심으로 한 공급 기사다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
