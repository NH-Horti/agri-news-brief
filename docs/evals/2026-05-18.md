## Daily Eval (2026-05-18)
- Overall: **97.15** (pass)
- Operational: **97.15**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=90.0, retrieval=85.0, section_fit=99.9, core=100.0, commodity=95.4
- Briefing cards: 16 / Commodity cards: 60
- Sections: supply:4/3 raw=207, policy:4/3 raw=114, dist:3/3 raw=35, pest:5/3 raw=65
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.69, fresh_72h=1.00, fit_avg=4.42, false_positive=0.00, weak_core=0.00, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **73.00** (target 95, needs_major_iteration)
- Components: article_selection=72.0, section_fit=66.0, core=70.0, summary=82.0, missed=68.0, noise=61.0
- Summary: 형식은 갖췄지만 기사 고르기는 아쉽다. 공급은 양파 사태 중복과 마늘 현장 기사의 약한 코어가 문제고, 정책은 이해당사자 요구·스마트팜 백필로 힘이 빠졌다. 유통은 농협 홍보성 기사 비중이 높고, 병해충은 사실상 동일한 과수화상병 기사 반복으로 지면 효율이 낮다. 원시 후보군에 보이는 더 나은 가격·수급 총괄 기사와 과수화상병 대표 기사로 더 날카롭게 짤 수 있었다.
- [high] duplication: 양파 농가들, '양파밭 갈아엎기 투쟁' 전개 / ‘ 양파 밭’ 싹 다 갈아엎었다…자식같이 키웠는데, 왜? - 같은 사건을 같은 섹션에 중복 배치했다.
- [high] weak_core: “작황 아쉽지만 값 잘 받았으면”…제주 남도종 마늘 수확 현장 - 현장 르포 성격이 강해 공급 핵심 이슈 대표성이 약하다.
- [medium] wrong_section: 가락시장 유통인, "시설현대화 국비 지원 확대·융자 금리 인하" 촉구 - 정책보다 유통업계 요구·시장 인프라 기사에 가깝다.
- [medium] weak_selection: 초기 비용만 수억 원대 스마트팜…실속 보급형도 고민해야 - 당일 핵심 농정 현안 대비 우선순위가 낮은 백필성 기사다.
- [high] promotional: 서익산 농협 , 블루베리 육성사업으로 농가소득 견인 - 개별 농협 성공사례 홍보 성격이 강하다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
