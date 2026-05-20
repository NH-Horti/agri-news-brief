## Daily Eval (2026-05-19)
- Overall: **97.85** (pass)
- Operational: **97.85**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.2, section_fit=92.4, core=100.0, commodity=97.2
- Briefing cards: 16 / Commodity cards: 56
- Sections: supply:5/3 raw=145, policy:3/3 raw=108, dist:4/3 raw=48, pest:4/3 raw=46
- Metrics: title_unique=1.00, domain_diversity=0.81, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.31, false_positive=0.00, weak_core=0.00, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.00** (target 95, needs_iteration)
- Components: article_selection=81.0, section_fit=79.0, core=84.0, summary=89.0, missed=80.0, noise=76.0
- Summary: 핵심 이슈인 양파 폭락과 과수화상병은 잘 잡았지만, 유통·정책 섹션에서 기사 성격이 약한 홍보성/지역 단신 비중이 높고 더 나은 후보를 일부 놓쳤다. 특히 dist는 실무 유통구조 기사보다 출하 개시·교육·선적식 중심으로 구성돼 섹션 정체성이 약해졌다.
- [high] wrong_section: "당도 꽉 찬 명품 멜론 출하 시작" 곡성멜론 본격 판매 - 출하 개시·지역 특산 홍보 성격이 강해 유통 구조 이슈로 약함.
- [high] promotional_filler: 동화청과, 청년농 경매 실전교육 - 교육 프로그램 소개로 뉴스 임팩트가 약하다.
- [medium] promotional_filler: 풍양농협, 2026년산 햇 마늘 산지경매장 개징 - 개장 행사성 지역 기사로 전국 독자 효용이 낮다.
- [medium] weak_policy_pick: 권요안 전북도의원, 양파 가격 폭락 대응 촉구 - 의원 촉구성 발언은 정책 결정·집행 기사보다 한 단계 약하다.
- [medium] duplicate_theme: 원주서 올해 강원 첫 과수화상병 발생…0.91㏊ 규모 - 1번 화상병 기사와 겹침이 커 정보 추가가 제한적이다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: dist, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
