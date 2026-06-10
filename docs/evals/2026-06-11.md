## Daily Eval (2026-06-11)
- Overall: **81.00** (warn)
- Operational: **96.10**
- Quality gate: **81.00** (needs_major_iteration, editorial_below_target; editorial=81.0, operational=96.1)
- Scores: completeness=100.0, diversity=90.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=96.9, commodity=91.2
- Briefing cards: 20 / Commodity cards: 30
- Sections: supply:5/5 raw=141, policy:5/5 raw=105, dist:5/5 raw=40, pest:5/5 raw=41
- Metrics: title_unique=1.00, domain_diversity=0.60, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.20, false_positive=0.00, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **81.00** (target 95, needs_major_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=78.0, section_fit=76.0, core=79.0, summary=88.0, missed=74.0, noise=72.0
- Summary: 섹션 수는 모두 채웠지만 편집 품질은 목표치에 못 미친다. 공급은 여름배추·양파는 적절했으나 가지 스마트재배를 1순위 코어로 세운 판단이 약하고, 더 강한 스마트APC/유통데이터 기사나 양파 가격회복 대책을 놓쳤다. 정책은 전국 수급점검 같은 상위 후보를 빼고 지역 협의회·복지 꾸러미·비농업 칼럼까지 넣어 가장 흔들렸다. 유통은 핵심 2건은 좋지만 후반 3건 중 복숭아 재배 현장 기사와 수상 기사성 아이템은 섹션 오배치에 가깝다. 병해충은 화상병 축을 잡았지만 실제 확산 수치가 큰 충북·홍성 발생 기사보다 모의훈련·중복 성격 점검 회의를 우선한 점이 아쉽다. 요약문 자체는 대체로 무난하나, 기사 선택의 정확성에서 감점이 크다.
- [high] wrong_section: [장용동의 우리들의 주거복지] 주택시장을 보는 대통령과 시장 간의 괴... - 농업 정책과 무관한 주택 칼럼이다.
- [high] filler: 춘천시, 기초생활 수급 노인에 농산물꾸러미 지원 - 지역 복지성 지원으로 정책 핵심성이 약하다.
- [medium] weak_core: "경험 대신 데이터로"…경기도 시설 가지 의 '스마트한 변신' - 현장기술 소개는 의미 있으나 당일 전국 수급 이슈 대비 코어 우선순위가 낮다.
- [high] missed_opportunity: 스마트 APC 성패여부, AI 기반 '산지 유통 데이터 공유'에 달렸다 - 당일성·산업 파급력이 큰 강한 후보를 공급/유통 어디서든 더 비중 있게 쓸 수 있었다.
- [high] wrong_section: 조래섭(전주원예농협 조합원) - 고온 다습 장마철 대비, 병해충 예방에... - 재배·병해충 현장기사로 유통 기사라고 보기 어렵다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
