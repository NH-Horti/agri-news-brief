## Daily Eval (2026-05-22)
- Overall: **96.99** (pass)
- Operational: **96.99**
- Scores: completeness=92.8, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=99.1, commodity=99.8
- Briefing cards: 18 / Commodity cards: 37
- Sections: supply:5/5 raw=155, policy:4/5 raw=170, dist:4/5 raw=51, pest:5/5 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.78, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.69, false_positive=0.00, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Section count gate: 98.0 (target_met)
- Score calibration: 88.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=87.0, section_fit=91.0, core=89.0, summary=94.0, missed=81.0, noise=84.0
- Summary: 전반적으로 양파 수급, 가격안정제도, 과수화상병 등 핵심 축은 잘 잡았지만 편집 완성도는 목표치 95에 못 미친다. 공급 섹션은 양파 이슈를 충분히 포착했으나 중복성이 강하고 약한 꼬리 카드가 섞였다. 정책과 유통은 raw pool이 충분한데도 각 4건에 그쳐 섹션 운영 점수를 깎으며, 특히 유통은 물류·시장운영보다 지역 판촉성 직거래 기사 비중이 아쉽다. 병해충은 화상병 경계 상향을 중심으로 가장 안정적이지만 지역 발생·주의 기사 반복이 있다. 요약문 자체는 대체로 유용하나, 더 강한 대체 후보를 일부 놓쳤다.
- [high] underfill: 정책 섹션 4건만 편성 - raw pool이 충분해 5건 기대치 충족 가능했다.
- [high] underfill: 유통 섹션 4건만 편성 - raw pool 51건으로 5건 구성이 가능했다.
- [medium] duplication: 양파 기사 과밀 편성 - 5건 중 다수가 같은 양파 가격급락 축을 반복한다.
- [medium] weak_tail: 햇 양파 공급과잉에 가격 급락…정부, 수출 확대로 돌파구 모색 - 기존 양파 기사들과 차별성이 약한 재탕형 꼬리다.
- [medium] weak_tail: 무안군, ' 양파 100톤' 수도권 직거래로 판로 뚫었다 - 지역 판촉성 직거래 기사로 유통 핵심성은 제한적이다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
