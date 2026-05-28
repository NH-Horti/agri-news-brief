## Daily Eval (2026-05-26)
- Overall: **87.04** (pass)
- Operational: **87.04**
- Scores: completeness=85.8, diversity=100.0, summary=100.0, freshness=40.0, retrieval=86.9, section_fit=100.0, core=100.0, commodity=95.5
- Briefing cards: 18 / Commodity cards: 38
- Sections: supply:5/5 raw=220, policy:4/5 raw=137, dist:4/5 raw=63, pest:5/5 raw=68
- Metrics: title_unique=1.00, domain_diversity=0.83, summary_presence=1.00, summary_numeric=0.78, fresh_72h=0.44, fit_avg=4.24, false_positive=0.00, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 98.0 (target_met)
- Components: article_selection=81.0, section_fit=80.0, core=84.0, summary=88.0, missed=76.0, noise=79.0
- Summary: 핵심 이슈인 양파·마늘 수급과 과수화상병은 대체로 잡았지만, 섹션 운용이 매끈하지 않습니다. 공급은 양파 편중과 출하성 로컬 기사 1건이 약하고, 정책은 주간 일정 카드가 명백한 약점입니다. 유통은 4장만 채운 데다 도매시장 AI 도입처럼 운영 현장성은 있으나 독자 효용이 낮은 카드가 들어갔고, 더 강한 양파 수출 기사도 놓쳤습니다. 병해충은 화상병 축은 맞았지만 코어로 넣은 주간농사메모는 섹션 적합성이 크게 떨어집니다. 전반적으로 읽을 만하지만, 원시 후보풀이 충분한 날 기준으로는 90점대 후반을 줄 수준은 아닙니다.
- [high] wrong_section: [주간농사메모]마늘·양파 가뭄 피해 방지 관수 실시 - 병해충보다 일반 재배관리 성격이 강함.
- [high] weak_core: [주간농사메모]마늘·양파 가뭄 피해 방지 관수 실시 - 코어로 삼기엔 긴급성·위험 신호가 약함.
- [high] filler: [정부 주요 일정] 경제·사회부처 주간 일정 (5월 25일 ~ 5월 29일) - 실질 정책 내용이 없는 일정 안내성 기사.
- [medium] missed_opportunity: "양파 값 살리자"…농협무역, 함양서 수출 드라이브 - 구체적 수출·판로 기사인데 유통 섹션에서 누락.
- [medium] filler: 예천 여름 대표 과일 '용궁 꿀 수박 ' 첫 출하… 촉성재배로 시장 선점 - 단순 첫 출하 로컬 홍보성에 가까움.

### Improvement Hints
- 최신성 점수가 내려갔습니다. 동일 이벤트 중 최신 기사 우선, 96시간 초과 기사 감점을 더 강하게 주는 편이 안정적입니다.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 오래된 기사일수록 배경 설명은 줄이고 이번 보고일 기준으로 새롭게 확인된 조치나 수급 신호를 먼저 적는다.
