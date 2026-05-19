## Daily Eval (2026-05-19)
- Overall: **49.79** (fail)
- Operational: **49.79**
- Scores: completeness=58.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=98.3, commodity=97.2
- Briefing cards: 5 / Commodity cards: 56
- Sections: supply:3/3 raw=146, policy:1/3 raw=109, dist:0/3 raw=49, pest:1/3 raw=47
- Metrics: title_unique=1.00, domain_diversity=1.00, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.85, false_positive=0.00, off_scope=0.00, story_dup=0.00, weak_core=0.00, commodity_weak=0.00, quality_penalty=40.5


### Editorial Shadow Eval
- Editorial: **41.00** (target 95, needs_major_iteration)
- Components: article_selection=35.0, section_fit=30.0, core=28.0, summary=70.0, missed=20.0, noise=32.0
- Summary: 핵심 이슈가 많은 날인데도 기사 선택이 크게 빗나갔다. 공급 1번은 수급 뉴스가 아니라 도매법인 교육성 기사라 코어로 부적절하고, 정책은 계란 수입 1건만 넣어 양파 가격 폭락·규제완화·가격안정기금 등 더 강한 정책 후보를 놓쳤다. 유통(dist) 섹션이 통째로 비어 있어 브리핑 구조도 무너졌다. 병해충은 과수화상병 선택이 적절했지만 전체적으로는 로컬 행사·홍보성·약한 유통 기사 선호와 섹션 오배치가 두드러진다.
- [high] wrong_section: 동화청과, 청년농 경매 실전교육 - 수급 동향보다 교육·홍보성 도매시장 기사다.
- [high] weak_core: 동화청과, 청년농 경매 실전교육 - 당일 시장가격·출하량·작황 충격이 없어 코어 가치가 낮다.
- [high] missed_opportunity: [전국 톡톡] 전국서 갈아엎는 양파 밭 - 양파값 폭락의 현장성과 피해 강도가 직거래장터 기사보다 크다.
- [high] coverage_gap: 유통 섹션 공란 - 논산 냉동딸기 수출, 가락시장 물류지원 등 쓸 만한 후보가 있었다.
- [high] missed_opportunity: 정책 선택 부족 - 계란 수입만으로는 정책면이 협소하고 양파 대책·규제합리화·가격안정기금 누락이 크다.
- [medium] promotional_filler: 세종청사 햇 양파 직거래장터… 양파 값 폭락에 최대 40% 할인 - 이슈는 있으나 행사 중심 서술이 강하다.
- [medium] noise: 벌써 3만 원 돌파라니…수박 가격 보고 깜짝 - 자극적 제목의 생활물가형 기사로 전문 브리핑 톤에 약하다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: policy, dist, pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
