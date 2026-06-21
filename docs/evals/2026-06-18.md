## Daily Eval (2026-06-18)
- Overall: **84.00** (warn)
- Operational: **93.34**
- Reader quality: **88.74** (capped; penalty=4.6, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **84.00** (needs_iteration, editorial_blocking_issue; editorial=84.0, operational=93.3)
- Scores: completeness=92.8, diversity=100.0, summary=100.0, freshness=100.0, retrieval=89.4, section_fit=96.7, core=96.0, commodity=88.0
- Briefing cards: 18 / Commodity cards: 21
- Sections: supply:4/5 raw=186, policy:5/5 raw=118, dist:4/5 raw=44, pest:5/5 raw=44
- Metrics: title_unique=1.00, domain_diversity=0.72, summary_presence=1.00, summary_numeric=0.78, fresh_72h=1.00, fit_avg=3.57, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.9, commodity_weak=0.00, commodity_items=6, commodity_active_today=10, commodity_active_today_unlinked=4, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.83, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 96.0 (soft_fallback)
- Components: article_selection=82.0, section_fit=80.0, core=83.0, summary=91.0, missed=79.0, noise=81.0
- Summary: 전반적으로 읽을 만한 브리핑이지만, 기사 고르기에서 정책·유통 섹션의 판단이 흔들렸다. 공급·병해충은 핵심 이슈를 대체로 잡았으나, 정책에 기업 지원 기사와 이벤트성 기사가 들어가고, 유통은 현장성은 있으나 수출·검역·실제 판로/물류 이슈보다 로컬 판촉 비중이 높다. 또 raw pool이 충분한데 supply·dist를 4장으로 마감해 편집 완성도가 95점대에 못 미친다.
- [high] wrong_section: 대아청과, 기후위기 여름채소 생산안정 지원 나서 - 정부 정책보다 기업 지원·상생 기사에 가깝다.
- [high] promotional_filler: 함양군, 양파 가격 하락에 고향사랑기부 연계 이벤트 실시 - 이벤트성 소비촉진 기사로 정책 핵심성이 약하다.
- [medium] weak_selection: 현장 - 한국과수농협연합회 중앙과수묘목관리센터 - 배경성 기관 소개로 당일 정책 의제성이 낮다.
- [medium] weak_selection: ‘비료 사용 처방 적정 시비 실천 캠페인’ 추진 - 캠페인 소식은 정책 강도가 낮고 시의성도 약하다.
- [high] missed_opportunity: 무주 사과농가 4년 연속 과수화상병 비상…올해 벌써 8곳 매몰 - 반복 발생·면적·재식재 공백이 뚜렷한 강한 화상병 기사인데 빠졌다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1), dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
