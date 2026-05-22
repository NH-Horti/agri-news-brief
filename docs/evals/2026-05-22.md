## Daily Eval (2026-05-22)
- Overall: **97.71** (pass)
- Operational: **97.71**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=95.4, core=94.1, commodity=97.2
- Briefing cards: 14 / Commodity cards: 43
- Sections: supply:3/3 raw=159, policy:4/3 raw=170, dist:3/3 raw=53, pest:4/3 raw=42
- Metrics: title_unique=1.00, domain_diversity=0.71, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=5.08, false_positive=0.00, weak_core=0.14, editorial_penalty=0.1, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Components: article_selection=82.0, section_fit=78.0, core=83.0, summary=90.0, missed=80.0, noise=79.0
- Summary: 핵심 이슈인 양파 수급난·가격안정제·과수화상병은 대체로 잘 잡았지만, 유통 섹션의 섹션 적합도와 코어 선정이 약했다. 특히 가락시장 하역노동 주5일제는 농산물 유통 구조 기사로 보기엔 노동 이슈 성격이 강하고, 기후변화 대응 스마트팜 기사는 유통면과 거리가 있다. 후보군에는 가락시장 파렛트 운송지원 확대, 세종 첫 과수화상병, 충북 현장진단실 등 더 직접적이고 강한 기사들이 보여 아쉬움이 남는다.
- [high] wrong_section: 가락시장 하역노동자, 주5일 일할 수 있을까? - 노동현안 중심으로 유통정책·물류 구조 변화 기사성 약함.
- [high] wrong_section: “스마트팜·신품종 보급…품목맞춤형 접근 필요” - 기후변화 생산기술 기사로 유통 섹션과 부적합.
- [medium] promotional_filler: 무안군, ' 양파 100톤' 수도권 직거래로 판로 뚫었다 - 지자체 판촉성 보도자료 성격이 강함.
- [high] missed_opportunity: "가락시장 물류 선진화 속도"…파렛트 운송지원 확대 - 유통면에 더 직접적이고 실무적인 후보를 놓침.
- [medium] missed_opportunity: 농진청, 과수화상병 확산 차단... 세종서 첫 과수화상병 확진 - 세종 첫 발생과 위기단계 상향은 전국성 파급력이 큼.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=7%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
