## Daily Eval (2026-06-05)
- Overall: **78.00** (warn)
- Operational: **92.74**
- Quality gate: **78.00** (needs_major_iteration, editorial_below_target; editorial=78.0, operational=92.7)
- Scores: completeness=92.8, diversity=100.0, summary=100.0, freshness=100.0, retrieval=88.1, section_fit=90.7, core=85.5, commodity=84.0
- Briefing cards: 18 / Commodity cards: 92
- Sections: supply:5/5 raw=162, policy:5/5 raw=122, dist:3/5 raw=90, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.89, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.30, false_positive=0.00, weak_core=0.17, editorial_penalty=0.4, commodity_weak=0.12, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **78.00** (target 95, needs_major_iteration)
- Section count gate: 97.5 (minimum_fallback)
- Components: article_selection=73.0, section_fit=66.0, core=68.0, summary=88.0, missed=76.0, noise=64.0
- Summary: 핵심 이슈인 양파 수급대책과 과수화상병은 잡았지만, 정책 섹션에 명백한 비관련 해외사 기사가 들어가고 유통 섹션이 3장에 그친 점이 크게 깎인다. 공급은 양파 과잉 대응 중심으로 잘 묶였으나 첫 출하성 지역 기사와 유사 양파 기사 중복이 보인다. 정책은 정부 1년 평가와 물가 대응 기사 자체는 의미가 있으나 링컨 기사 오배치가 치명적이다. 유통은 온라인도매시장·양파 수출·중동전쟁 현장애로 기사로 방향은 맞지만, raw pool이 충분한데도 5장을 채우지 못했고 더 강한 수출/온라인 판매 후보를 놓쳤다. 병해충은 과수화상병 중심 편성은 적절하나 청주 예찰성 기사 비중이 높고 고양 신규 발생 같은 더 강한 발생 기사 비중을 높였어야 한다.
- [high] wrong_section: 미국 독립 250주년 기념 / 링컨의 리더십과 남북전쟁 ④ 내전, 외교전, ... - 농정·수급·유통·병해충과 무관한 해외사다.
- [high] underfill: 유통 섹션 3건만 편성 - raw candidates 90건인데 최소 fallback에 머물렀다.
- [medium] weak_core: 예천 개포면, 첫 풋고추 출하로 소비자 입맛 사로잡아 - 지역 첫 출하 소식은 전국 수급 핵심성 낮다.
- [medium] duplication: '공급과잉 양파 ' 수출로 수급 안정…대만에 초도물량 100t 수출 - 1번 양파 대책과 같은 축의 후속으로 지면 효율이 떨어진다.
- [medium] missed_opportunity: 고품질 ‘애플수박’ 첫 온라인 판매 나서 - 온라인 판매·판로 확대의 구체성이 높아 유통 적합도가 높다.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: dist. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 6%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
