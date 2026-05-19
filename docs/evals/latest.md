## Daily Eval (2026-05-19)
- Overall: **49.79** (fail)
- Operational: **49.79**
- Scores: completeness=58.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=98.3, commodity=97.2
- Briefing cards: 5 / Commodity cards: 56
- Sections: supply:3/3 raw=144, policy:1/3 raw=109, dist:0/3 raw=48, pest:1/3 raw=47
- Metrics: title_unique=1.00, domain_diversity=1.00, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.85, false_positive=0.00, off_scope=0.00, story_dup=0.00, weak_core=0.00, commodity_weak=0.00, quality_penalty=40.5


### Editorial Shadow Eval
- Editorial: **34.00** (target 95, needs_major_iteration)
- Components: article_selection=28.0, section_fit=22.0, core=26.0, summary=66.0, missed=18.0, noise=20.0
- Summary: 핵심 이슈가 보이는 후보풀을 두고도 섹션 구성이 크게 어긋났습니다. 공급에 도매법인 교육·직거래 장터·수박 소비물가를 몰아넣고, 정작 유통(dist) 섹션은 비워 두었으며 정책도 계란 1건만 골라 양파·규제완화·가격안정기금 등 더 강한 정책 후보를 놓쳤습니다. 요약문 자체는 수치와 맥락이 있어 읽히지만, 기사 선정이 신문형 브리핑 기준에서 약합니다.
- [high] wrong_section: 동화청과, 청년농 경매 실전교육 - 도매시장 유통·교육 기사로 공급 수급 핵심이 아님.
- [high] missing_section: 유통 섹션 공백 - dist 후보군에 수출·산지경매·물류개선 기사가 충분한데 0건 선택.
- [high] weak_core: 세종청사 햇 양파 직거래장터… 양파 값 폭락에 최대 40% 할인 - 정책성 소비촉진 행사 성격이 강하고 공급 섹션 대표성은 약함.
- [high] promotional_filler: 동화청과, 청년농 경매 실전교육 - 기업 프로그램 소개 성격이 강한 홍보성 기사.
- [high] missed_opportunity: [전국 톡톡] 전국서 갈아엎는 양파 밭 - 가격 폭락의 현장성과 심각도가 직거래장터보다 훨씬 큼.
- [high] missed_opportunity: 농식품규제 합리화 50건 / 평창 가격안정기금 - 정책 섹션에 계란 1건만 넣어 정책 폭과 무게감이 부족.
- [medium] selection_balance: 수박 가격 급등 기사 편중 - 공급 3건 중 2건이 소비가격·판촉 성격으로 수급 구조 정보가 빈약.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: policy, dist, pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
