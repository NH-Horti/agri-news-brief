## Daily Eval (2026-05-22)
- Overall: **98.47** (pass)
- Operational: **98.47**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=99.6, core=100.0, commodity=91.3
- Briefing cards: 15 / Commodity cards: 42
- Sections: supply:3/3 raw=156, policy:4/3 raw=172, dist:3/3 raw=53, pest:5/3 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.73, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=5.03, false_positive=0.00, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=85.0, section_fit=87.0, core=88.0, summary=92.0, missed=79.0, noise=84.0
- Summary: 핵심 현안인 양파 수급난·가격안정제·과수화상병은 잘 잡았지만, dist와 pest의 꼬리 기사 선택이 다소 약하고 policy 4번째 카드의 범용 물가 기사도 농업 일간 브리프 기준으론 우선순위가 낮다. 특히 dist는 더 직접적인 수출·우회물류 기사와 비교해 정부 대응 기사-실적 기사 중복감이 있고, pest는 화상병 확산 국면에서 일반 예찰성 지역 기사 비중이 과하다. 전반적으로 읽을 만하지만 95점대에 줄 만큼 날카로운 선별은 아니다.
- [medium] weak_tail: 중동發 원자재 충격 현실화···4월 생산자물가 28년 만에 최대 상승 - 농업정책 직접성 낮은 거시 물가 기사다.
- [medium] duplication: 중동발 충격 확산…정부, K-푸드 물류·플라스틱 고용 방어 총력 - 같은 날 수출 실적 기사와 묶이며 물류 이슈가 중복된다.
- [medium] missed_opportunity: K-푸드 수출 , 중동 물류 위기 속 37.6% 성장 기록 - 선택본보다 뉴시스발 중동 우회·지원 규모 설명 기사가 더 구체적이다.
- [medium] weak_tail: 서천군 농업기술센터, 밭작물 병해충 예찰 강화 - 일반적 지역 예찰 공지 성격이 강하다.
- [medium] weak_tail: 안동시, 고추 진딧물·총채벌레 급증 우려…"적기 방제 당부" - 지역 행정 당부형 기사로 전국성·구체성이 약하다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
