## Daily Eval (2026-05-19)
- Overall: **98.81** (pass)
- Operational: **98.81**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=100.0, commodity=97.2
- Briefing cards: 17 / Commodity cards: 57
- Sections: supply:5/3 raw=146, policy:4/3 raw=113, dist:4/3 raw=51, pest:4/3 raw=47
- Metrics: title_unique=1.00, domain_diversity=0.76, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.58, false_positive=0.00, weak_core=0.00, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **72.00** (target 95, needs_major_iteration)
- Components: article_selection=70.0, section_fit=68.0, core=66.0, summary=84.0, missed=63.0, noise=67.0
- Summary: 핵심 이슈인 양파 폭락·과수화상병은 잡았지만, 유통·정책 섹션에 행사성·지역 홍보성 카드가 섞였고 같은 이슈의 중복도 보인다. 특히 dist는 시장 구조·물류 변화보다 출하 시작/교육 기사 비중이 커 약하다. raw pool에 보이는 더 적합한 정책·유통 후보를 일부 놓쳐 목표점수에는 못 미친다.
- [high] wrong_section: 권요안 전북도의원, 양파 가격 폭락 대응 촉구 - 현장 촉구성 발언 기사로 정책 확정·집행 정보가 약함.
- [high] wrong_section: "당도 꽉 찬 명품 멜론 출하 시작" 곡성멜론 본격 판매 - 출하 개시·지역 특산 홍보 성격이 강함.
- [high] promotional: 동화청과, 청년농 경매 실전교육 - 업체 프로그램 소개로 공익적 유통 이슈성 낮음.
- [medium] duplicate: 충주·원주서 ‘과수화상병’…이른 더위에 예상보다 발생 빨라 / 원주서 올해 강원 첫 과수화상병 발생…0.91㏊ 규모 - 같은 화상병 발생 축을 반복해 정보 증분이 작음.
- [medium] duplicate: 한 통에 3만원… 이른 더위에 수박값 껑충 / [친절한 경제] 수박 한 통에 3만 원… 가격 널뛰는 여름 과일들 - 같은 가격 급등 이슈를 두 장으로 반복.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
