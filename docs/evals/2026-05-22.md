## Daily Eval (2026-05-22)
- Overall: **98.15** (pass)
- Operational: **98.15**
- Scores: completeness=100.0, diversity=96.7, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=99.1, commodity=97.2
- Briefing cards: 12 / Commodity cards: 43
- Sections: supply:3/3 raw=158, policy:3/3 raw=169, dist:3/3 raw=54, pest:3/3 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.67, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.86, false_positive=0.00, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Section count gate: 100.0 (target_met)
- Score calibration: 88.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=87.0, section_fit=90.0, core=88.0, summary=92.0, missed=84.0, noise=89.0
- Summary: 전반적으로 당일 농정 핵심 이슈를 잘 잡았고 섹션 수량도 충족했다. 다만 공급 섹션이 양파 3건으로 과밀해 중복감이 크고, 유통 섹션은 물류·수출 기사 선택은 맞지만 가락시장 운영·도매시세 등 더 직접적인 운영 기사 활용 여지가 있었다. 병해충은 과수화상병 경계 격상과 지역 발생을 잡은 점은 좋으나, 경기 첫 발생 기사 등 더 강한 전국 확산 신호를 놓친 점이 아쉽다. 그래서 90점대 초반은 가능하지만 95점 이상급 편집이라고 보긴 어렵다.
- [medium] duplication: 양파 3건 집중 편성 - 가격폭락·비축지연·정부대응이 모두 양파로 묶여 섹션 다양성이 약하다.
- [medium] missed_opportunity: [한눈에 보는 시세] 양배추 약세 기사 미채택 - 도매시세 기반의 직접 가격 기사로 공급 섹션 균형 보완 가치가 있었다.
- [medium] weak_tail: 햇 양파 공급과잉에 가격 급락…정부, 수출 확대로 돌파구 모색 - 앞선 두 양파 기사와 내용 중복이 크고 새 정보 밀도가 낮다.
- [medium] missed_opportunity: 유통 섹션 핵심감 다소 약함 - 파렛트 지원은 적합하지만 임팩트가 약하고 더 직접적인 도매시장 운영·시세 기사 풀이 있었다.
- [low] duplication: 중동 수출·물류 기사 2건 병행 - 두 기사 모두 같은 정부 메시지와 수출 증가 프레임이 겹친다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
