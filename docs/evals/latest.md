## Daily Eval (2026-05-22)
- Overall: **97.12** (pass)
- Operational: **97.12**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=95.9, core=100.0, commodity=97.2
- Briefing cards: 15 / Commodity cards: 44
- Sections: supply:4/3 raw=170, policy:3/3 raw=169, dist:4/3 raw=60, pest:4/3 raw=45
- Metrics: title_unique=1.00, domain_diversity=0.73, summary_presence=1.00, summary_numeric=0.87, fresh_72h=1.00, fit_avg=4.75, false_positive=0.00, weak_core=0.00, editorial_penalty=1.2, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Components: article_selection=80.0, section_fit=76.0, core=81.0, summary=88.0, missed=79.0, noise=84.0
- Summary: 전반적으로 당일 농업 현안은 포착했지만, 섹션별 편집 판단은 들쭉날쭉했다. 공급은 양파 약세 이슈를 잘 잡았으나 비핵심보다 약한 감귤 화장품 기사를 코어로 둔 점이 치명적이다. 정책은 농협 개혁·애그플레이션을 담아 무난했지만, 농안법 가격안정제도나 밀가루 담합 같은 더 농업정책 밀착형 후보를 놓쳤다. 유통은 교육·직거래성 기사 비중이 높아 산업 구조 변화나 물류 이슈 중심성이 약했다. 병해충은 과수화상병 축을 잡았지만 전국 확산 경보·세종 첫 발생 같은 상위 이슈를 비켜가 중복 대비 효율이 떨어졌다.
- [high] wrong_core: 국산 감귤 , 기능성 화장품으로 대변신 - 수급보다 바이오소재 홍보성에 가까워 핵심 공급 기사로 부적절.
- [high] missed_opportunity: 농산물가격안정제도 8월 시행…“평균가격, 경영비 밑돌땐 차액 지원” - 양파 폭락 국면과 직접 맞닿은 제도 변화인데 미선정.
- [high] section_mismatch: “스마트팜·신품종 보급…품목맞춤형 접근 필요” - 유통보다 생산기술·기후대응 성격이 강함.
- [high] weak_pick: [동화청과 유통교육] "맛·품질은 기본…소비자 선택 기준까지 설계 필... - 교육 행사성 기사로 유통 섹션 대표성 부족.
- [medium] promotional_filler: 무안군, ' 양파 100톤' 수도권 직거래로 판로 뚫었다 - 지자체 소비촉진 보도자료 성격이 강함.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=7%, pest_theme_duplicate=13%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
