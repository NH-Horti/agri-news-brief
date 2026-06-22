## Daily Eval (2026-06-23)
- Overall: **81.00** (warn)
- Operational: **98.20**
- Reader quality: **86.00** (capped; penalty=2.6, cap=86.0, reasons=commodity_pool_false_link, commodity_pool_false_link_severe)
- Quality gate: **81.00** (needs_major_iteration, editorial_blocking_issue; editorial=81.0, operational=98.2)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=100.0, core=95.4, commodity=95.6
- Briefing cards: 20 / Commodity cards: 52
- Sections: supply:5/5 raw=200, policy:5/5 raw=117, dist:5/5 raw=52, pest:5/5 raw=35
- Metrics: title_unique=1.00, domain_diversity=1.00, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.51, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=12, commodity_active_today=17, commodity_active_today_unlinked=5, commodity_coverage=0.36, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.20, commodity_dominant_section=0.58, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **81.00** (target 95, needs_major_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=79.0, section_fit=78.0, core=80.0, summary=90.0, missed=74.0, noise=77.0
- Summary: 섹션 수는 모두 채웠지만, 실제 편집 선택은 양파 중복과 지역·홍보성 보강이 많아 점수가 깎입니다. 공급은 같은 전북 양파 대책을 중복 채택했고 토마토 수출 검역 완화는 dist 성격이 강합니다. 정책은 핵심 2건은 괜찮지만 칼럼과 지역 물가 기사 비중이 높아 약합니다. dist는 유통 현안보다 지원·개장식·브리핑성 기사가 많고, 보이는 더 강한 후보인 도매시장 해킹 사고를 놓친 점이 큽니다. pest는 과수화상병 중심축은 맞지만 탄저병 2건과 정읍 고추 안내는 하위 꼬리 수준입니다. 요약문 자체는 대체로 명확합니다.
- [high] duplication: 전북도, 양파 가격 하락에…시장격리와 소비촉진 대책 추진 / 전북도 양파 가격 안정 총력 - 동일 전북 양파 대책을 사실상 중복 채택했다.
- [high] wrong_section: 국산 토마토 , 수출식물검역증명서만으로 일본 수출 가능 - 수급보다 수출·검역·통관 완화 성격이 강하다.
- [medium] weak_core: 전북도, 양파 가격 하락에…시장격리와 소비촉진 대책 추진 - 전국 충격이 큰 양파 폭락 현장 기사보다 정책발표물이 1순위다.
- [medium] promotional_filler: [편집자 칼럼] 저출산의 부메랑이 농식품 시장을 강타하고 있다 - 의견성 칼럼으로 정책 정보 가치가 낮다.
- [medium] weak_selection: 장바구니 덮친 이른 무더위…먹거리 물가 '고공행진' - 지역 물가 재전달로 전국 정책 섹션에 비해 급이 약하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
