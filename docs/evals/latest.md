## Daily Eval (2026-07-16)
- Overall: **86.73** (pass)
- Operational: **93.17**
- Reader quality: **91.67** (capped; penalty=1.5, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **86.73** (needs_major_iteration, editorial_major_issue; editorial=78.2, operational=93.2)
- Scores: completeness=92.8, diversity=93.0, source=93.3, summary=98.3, freshness=100.0, retrieval=86.6, section_fit=100.0, core=97.3, commodity=77.9
- Briefing cards: 18 / Commodity cards: 59
- Sections: supply:5/5 raw=198, policy:5/5 raw=124, dist:5/5 raw=113, pest:3/5 raw=26
- Metrics: title_unique=1.00, domain_diversity=0.67, low_tier=0.17, summary_presence=1.00, summary_numeric=0.72, fresh_72h=1.00, fit_avg=5.05, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=10, commodity_active_today=17, commodity_active_today_unlinked=7, commodity_coverage=0.30, commodity_strict_link=0.70, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.60, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **78.25** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 78.30; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min, no_section_underfill, commodity_board_score_min)
- Section count gate: 97.5 (minimum_fallback)
- Components: article_selection=80.0, section_fit=86.0, core=76.0, summary=79.0, missed=72.0, noise=75.0
- Summary: 전반적으로 주요 농정·유통 이슈는 잡았지만, 공급 섹션의 동일 기사 중복 코어 선정, 홍보성 꼬리기사, 병해충 섹션 3건 underfill, 그리고 병해충·물류 후보 누락이 크게 깎입니다. 요약도 일부 카드에서 보일러플레이트·문장 절단·반복이 보여 독자용 완성도가 떨어집니다.
- [major] duplicate_story: 2026~2027년산 제주 월동무 ·양배추 재배면적 감소 전망 - 1번 카드와 같은 제주 월동채소 재배면적 전망을 다른 매체로 반복했고 둘 다 코어로 처리됐다.
- [moderate] promotional_filler: 도로공사, 김천 샤인머스캣 업사이클링…취약계층 아동 돕는다 - 공급 과잉 언급은 있으나 본질은 기관 사회공헌·판매 홍보성 행사다.
- [moderate] promotional_filler: 킴스클럽, 여름 제철 국산 햇 사과 '썸머킹' 출시... - 개별 유통사 상품 출시 홍보에 가깝고 요약도 ')'로 시작해 품질이 낮다.
- [major] underfill: pest 섹션 3건만 선정 - raw 후보가 26건 있는데 목표 5건 대비 3건에 그쳐 병해충 섹션이 최소 fallback에 머물렀다.
- [moderate] missed_candidate: 비 소강, 당분간 무더위 … 농작물 병해 예방 사전 관리 중요 - 농진청 중앙 예찰단과 9개 작목 병해 위험을 다룬 전국 단위 후보가 선택되지 않았다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
