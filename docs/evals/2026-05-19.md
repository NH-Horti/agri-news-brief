## Daily Eval (2026-05-19)
- Overall: **90.29** (pass)
- Operational: **90.29**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=89.4, core=100.0, commodity=97.2
- Briefing cards: 16 / Commodity cards: 57
- Sections: supply:5/3 raw=146, policy:4/3 raw=110, dist:3/3 raw=49, pest:4/3 raw=47
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.57, false_positive=0.06, off_scope=0.06, story_dup=0.06, weak_core=0.00, commodity_weak=0.00, quality_penalty=7.2


### Editorial Shadow Eval
- Editorial: **72.00** (target 95, needs_major_iteration)
- Components: article_selection=68.0, section_fit=61.0, core=58.0, summary=82.0, missed=66.0, noise=54.0
- Summary: 핵심 기사 선택이 전반적으로 약합니다. 공급·유통에서 홍보성/출하개시성 기사와 잘못된 섹션 배치가 많고, 방제 섹션은 화상병 중복 비중이 높습니다. 정책 섹션의 계란 수급 대책은 적절하지만, 더 직접적인 유통·물류 개선 기사와 양파 소비촉진/수급대책을 더 잘 배치할 수 있었습니다.
- [high] wrong_section: 동화청과, 청년농 경매 실전교육 - 수급 이슈보다 유통교육 기사다.
- [high] weak_core: 동화청과, 청년농 경매 실전교육 - 공급 섹션 코어로는 시장 영향이 약하다.
- [high] wrong_section: "당도 꽉 찬 명품 멜론 출하 시작" 곡성멜론 본격 판매 - 단순 출하 개시·지역 홍보성에 가깝다.
- [high] missed_opportunity: 서울시공사, 물류 선진화 위해 순회수집 운송지원 확대 - 유통 섹션에 더 직접적인 시장 인프라 기사였다.
- [medium] duplicate: 충주·원주서 ‘과수화상병’…이른 더위에 예상보다 발생 빨라 / 원주서 올해 강원 첫 과수화상병 발생…0.91㏊ 규모 - 동일 이슈 중복으로 정보 효율이 낮다.
- [medium] noise: 한국향 두리안 수출 262% 급증에도...울상짓는 베트남 농가? - 국내 농정 독자 관점에서 비중이 낮다.
- [medium] duplicate: 평창군, 908개 농가에 농산물 가격안정 기금 21억 지원 / 평창군, 농축산물 가격 안정 기금 21억 지원 …908농가 '숨통' - 유사 기사 중복 채택이다.
- [medium] missed_opportunity: 농식품부, 양파 소비 촉진 행사…농산물 할인 이달 말까지 연장 - 양파 가격 급락 대응의 직접 정책기사인데 빠졌다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 동일 사건 카드가 반복 노출됩니다 (비율 6%). URL·제목만 보지 말고 숫자·지역·주체를 묶은 story signature로 섹션 간 중복을 줄이세요.
- 해외 비관리 품목 카드가 브리핑에 섞였습니다 (비율 6%). 국내 정책·수급·가격 안정 연결고리가 없으면 해당 품목어를 다음 선별 가드레일에 반영하세요.
- 국내 원예·수급 브리핑 범위 밖 기사가 포함되어 있습니다 (비율 6%). 해외 품목 동향, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
