## Daily Eval (2026-06-01)
- Overall: **82.00** (warn)
- Operational: **94.73**
- Quality gate: **82.00** (needs_iteration, editorial_below_target; editorial=82.0, operational=94.7)
- Scores: completeness=100.0, diversity=90.0, summary=100.0, freshness=94.3, retrieval=88.8, section_fit=92.5, core=100.0, commodity=90.5
- Briefing cards: 20 / Commodity cards: 60
- Sections: supply:5/5 raw=220, policy:5/5 raw=117, dist:5/5 raw=110, pest:5/5 raw=84
- Metrics: title_unique=1.00, domain_diversity=0.60, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=3.90, false_positive=0.00, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=78.0, core=76.0, summary=88.0, missed=84.0, noise=82.0
- Summary: 카드 수는 전 섹션 목표치 5장을 채웠지만, 실제 편집 품질은 그보다 낮다. 정책은 가격안정제와 중동발 농자재 수급 이슈를 잡아 비교적 강했으나, 같은 주제 중복과 약한 보충 카드가 보인다. 공급은 핵심 기사 선정이 크게 빗나갔고 지역 출하·판촉성 기사 비중이 높다. 유통은 온라인도매시장·출하 채널 변화보다 정부 애로접수 기사와 교육 성료 기사가 앞서 약하다. 병해충은 화상병 중심 축은 맞지만 전국 확산 총괄 기사나 더 강한 발생 집계 기사 대신 지역 단신이 섞여 아쉽다. 형식은 충족했지만 기사 고르기 자체는 90점대에 못 미친다.
- [high] wrong_core: 좋은 농사란 ‘무엇을 넣을 것인가’보다 - 수급·공급 이슈가 아닌 일반 재배 칼럼 성격이다.
- [medium] section_misfit: 천안 수신 멜론 본격 출하 …"초여름 입맛 사로잡는다" - 단순 출하 홍보성 지역 기사로 공급 섹션 가치가 낮다.
- [medium] filler: 함양군·함양농협, 양파 수급 안정 총력 대응 - 지역 판촉·수출 계획성 보도라 전국 공급 판단 자료가 약하다.
- [medium] duplication: 농산물가격안정제 관련 3건 동시 선택 - 핵심 의제는 맞지만 설명·비평이 과밀해 다른 정책 이슈를 밀어냈다.
- [medium] weak_tail: [비즈톡톡] 복날은 아직인데 들썩이는 삼계탕값… - 외식가 기사로 농정·제도 맥락이 약하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 품목명 직접 언급, 수급/가격 신호, representative rank 상위 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
