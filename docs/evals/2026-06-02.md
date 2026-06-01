## Daily Eval (2026-06-02)
- Overall: **82.00** (warn)
- Operational: **96.85**
- Quality gate: **82.00** (needs_iteration, editorial_below_target; editorial=82.0, operational=96.8)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=83.1, section_fit=97.2, core=92.5, commodity=97.2
- Briefing cards: 20 / Commodity cards: 20
- Sections: supply:5/5 raw=119, policy:5/5 raw=76, dist:5/5 raw=55, pest:5/5 raw=67
- Metrics: title_unique=1.00, domain_diversity=1.00, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=4.19, false_positive=0.00, weak_core=0.14, editorial_penalty=0.8, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=79.0, section_fit=76.0, core=78.0, summary=83.0, missed=84.0, noise=75.0
- Summary: 구색은 5개 섹션×5개를 모두 채웠지만, 실제 편집 품질은 그보다 낮다. 공급은 품종 추천·토종 생강처럼 홍보성/장기맥락성 기사가 핵심 슬롯을 잠식했고, 정책은 같은 현장점검 기사 3건이 중복돼 지면 낭비가 크다. 유통은 도매시장 정산 시스템 자체는 적절하지만 동일 이슈 중복과 지역 출하 홍보성 체리 기사로 약하다. 병해충은 과수화상병 중심 축은 맞지만 유사한 확산 기사 비중이 높고, 충북 누적 피해 같은 더 구체적인 현황 기사를 놓친 점이 아쉽다. 형식적 완성도는 높아도 기사 선택은 95점대와 거리가 있다.
- [high] wrong_priority: 6월 이달의 추천품종 - 품종 홍보성 성격이 강해 수급 핵심 기사로 부적절.
- [high] filler: 전북도 연구사업과 종자주권 자긍심이 토종 생강 살렸다 - 당일 수급 이슈보다 장기 사례 소개에 가깝다.
- [high] duplication: 여름 물가 지킨다 / 김종구 차관… / 폭염·열대야 예고… - 동일 현장점검 기사 3건 반복으로 지면 효율 저하.
- [medium] missed_better_candidate: 농식품부, 피해 농가 323곳 이달 지원금 지급…재해 후속 조치 - 실질 지원정책 기사인데 중복 점검 기사에 밀렸다.
- [medium] duplication: 대구 도매시장 유통 투명해진다… / 농협은행, 대구도매 시장에 출하대금정산시스템 도입 - 같은 정산시스템 이슈를 2건 실었다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: supply, dist, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
