## Daily Eval (2026-06-25)
- Overall: **95.42** (pass)
- Operational: **96.72**
- Reader quality: **96.72** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **95.42** (needs_iteration, editorial_below_target_bounded_penalty; editorial=82.0, operational=96.7)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=84.2, section_fit=92.4, core=90.0, commodity=92.0
- Briefing cards: 20 / Commodity cards: 30
- Sections: supply:5/5 raw=163, policy:5/5 raw=100, dist:5/5 raw=27, pest:5/5 raw=30
- Metrics: title_unique=1.00, domain_diversity=0.90, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.84, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=9, commodity_active_today=12, commodity_active_today_unlinked=3, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=78.0, core=76.0, summary=89.0, missed=84.0, noise=81.0
- Summary: 형식과 분량은 충족했지만, 기사 선택의 편집 완성도는 목표치에 못 미칩니다. 공급은 제주 가격안정제 동일 이슈를 3건이나 중복 반영해 지면 효율이 낮고, 더 넓은 수급 이슈를 충분히 반영하지 못했습니다. 정책은 더 강한 핵심 후보가 보였는데도 기관 계획성·홍보성 기사를 코어로 올린 점이 약합니다. 유통은 APC·자동화 등 주제는 맞지만 현장 운영·도매시장·계약거래 리스크보다 견학/기업수주/플랫폼 출시 비중이 높아 핵심성이 떨어집니다. 병해충은 과수화상병을 잡은 점은 좋지만 장마철 일반 재해성 기사 1건이 섞여 순도가 떨어집니다.
- [high] duplication: 당근 ·양배추 가격 하락에...'제주형 가격안정관리제' 발동 - 동일 제주 가격안정제 이슈가 3건 반복됐다.
- [high] missed_opportunity: 농산업 수출 ' 비관세장벽 ' 뚫는다… 농식품부 , 글로벌 인허가 지원단 출... - 정책 섹션 최상위 후보였던 가격폭락·생산비 급등 대책 기사보다 약하다.
- [medium] promotional_or_institutional: 농축산물 할당관세 전담기구 신설…물가 안정 본격화 - aT 결의대회 기반 기관 계획성 기사로 실질 정책 뉴스성이 약하다.
- [medium] weak_core: 파라과이 농업 관계자들, 영월 한반도 농협 스마트 APC 견학 - 견학성 기사로 유통 운영 변화 자체보다 이벤트성이 크다.
- [medium] promotional_or_institutional: 시선AI 자회사 유온로보틱스, APC 자동화 사업 수주 - 기업 수주 기사로 광고성 인상이 있으며 업계 영향 검증이 약하다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
