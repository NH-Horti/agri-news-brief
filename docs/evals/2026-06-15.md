## Daily Eval (2026-06-15)
- Overall: **84.00** (warn)
- Operational: **94.73**
- Reader quality: **93.98** (capped; penalty=0.8, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **84.00** (needs_iteration, editorial_blocking_issue; editorial=84.0, operational=94.7)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=90.8, retrieval=86.9, section_fit=100.0, core=86.6, commodity=96.8
- Briefing cards: 19 / Commodity cards: 21
- Sections: supply:5/5 raw=246, policy:4/5 raw=124, dist:5/5 raw=47, pest:5/5 raw=36
- Metrics: title_unique=1.00, domain_diversity=0.74, summary_presence=1.00, summary_numeric=0.74, fresh_72h=1.00, fit_avg=3.94, false_positive=0.00, hard_reader_issues=0, weak_core=0.20, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=9, commodity_active_today=15, commodity_active_today_unlinked=6, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.56, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=82.0, section_fit=86.0, core=83.0, summary=92.0, missed=76.0, noise=79.0
- Summary: 전반적으로 기사 요약과 기본 섹션 구성은 갖췄지만, 편집 선택은 95점대와 거리가 있다. 공급 섹션에 행사성·지원성 filler가 과하고, 유통 섹션은 일본 도매시장 기사가 중복적으로 소비되며 더 강한 온라인도매시장 비판 기사를 놓쳤다. 병해충은 화상병 핵심 이슈를 잡았지만 우박 기사 2건은 주제 적합성이 떨어진다. 정책은 4건 soft fallback이라 상한도 낮다.
- [high] wrong_section: “ 양파 즙 한잔하며 쉬었다 가세요”…농협, 폭염 대비 쉼터 지원 강화 - 수급보다 복지·현장지원 기사다.
- [high] promotional_filler: 농협유통 하나로마트, ' 양배추 ' 소비 촉진행사...농촌과 상생 협력 - 판촉행사 비중이 커 공급 핵심성이 약하다.
- [high] missed_opportunity: 온라인도매시장, 왜 나랏돈 퍼주는 '곳간' 됐나 - 유통 구조 비판성과 현안성이 큰데 미선정.
- [medium] duplication: 오타도매시장, '저장·분류·배송' 종합 유통 플랫폼 / 요코하마도매시장 '소매 분산 물류'로 특화 - 둘 다 일본 도매시장 사례로 결이 유사하다.
- [medium] wrong_section: “양배추 잎에 동전만 한 구멍”⋯기습우박에 강원 농경지 20만평 피해 - 병해충이 아니라 기상재해다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
