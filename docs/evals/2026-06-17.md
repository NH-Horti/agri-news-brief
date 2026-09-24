## Daily Eval (2026-06-17)
- Overall: **84.00** (warn)
- Operational: **91.85**
- Reader quality: **89.60** (capped; penalty=2.2, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **84.00** (needs_iteration, editorial_blocking_issue; editorial=84.0, operational=91.8)
- Scores: completeness=89.2, diversity=100.0, summary=100.0, freshness=100.0, retrieval=79.8, section_fit=100.0, core=100.0, commodity=78.4
- Briefing cards: 17 / Commodity cards: 44
- Sections: supply:4/5 raw=277, policy:4/5 raw=128, dist:4/5 raw=59, pest:5/5 raw=28
- Metrics: title_unique=1.00, domain_diversity=0.71, summary_presence=1.00, summary_numeric=0.76, fresh_72h=1.00, fit_avg=4.08, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=8, commodity_active_today=15, commodity_active_today_unlinked=7, commodity_coverage=0.24, commodity_strict_link=0.75, commodity_false_link=0.00, commodity_dominant_section=0.75, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 94.0 (soft_fallback)
- Components: article_selection=82.0, section_fit=80.0, core=78.0, summary=90.0, missed=81.0, noise=79.0
- Summary: 양파 가격 하락과 과수화상병 등 당일 핵심 이슈는 일부 잘 잡았지만, 섹션 배치와 코어 선정이 고르지 못하다. 특히 pest의 코어 오선정, dist의 약한 로컬 출하식·휴장 기사 비중, supply·policy·dist의 4장 소프트 폴백이 모두 겹쳐 편집 완성도를 깎았다. 원시 후보풀에는 더 나은 dist 기사와 pest 보강 후보가 보여 고득점은 어렵다.
- [high] wrong_section: 대전 유성농협·고향주부모임, 배농가 찾아 봉지 씌우기 도와 - 병해충 기사 아닌 일손돕기다.
- [high] weak_core: 대전 유성농협·고향주부모임, 배농가 찾아 봉지 씌우기 도와 - 코어로 뽑기엔 이슈성·위험도 낮다.
- [high] missed_opportunity: 구리시장 7월15일 시범휴업 안한다 - 도매시장 운영 변화라는 더 강한 유통 핵심 후보를 놓쳤다.
- [medium] promotional_filler: 진천 덕산농협, ‘생거진천 오감드레 꿀수박’ 출하 나서 - 실무 유통 이슈보다 출하식 성격이 강하다.
- [medium] weak_selection: 청송군 농산물산지공판장 8월까지 휴장 - 휴장 공지는 운영 참고성은 있으나 임팩트 약하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: supply, policy, dist, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1), policy(-1), dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
