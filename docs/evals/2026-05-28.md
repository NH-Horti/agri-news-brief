## Daily Eval (2026-05-28)
- Overall: **82.00** (warn)
- Operational: **98.18**
- Quality gate: **82.00** (needs_iteration, editorial_below_target; editorial=82.0, operational=98.2)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=100.0, core=100.0, commodity=96.6
- Briefing cards: 20 / Commodity cards: 38
- Sections: supply:5/5 raw=142, policy:5/5 raw=90, dist:5/5 raw=31, pest:5/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=5.09, false_positive=0.00, weak_core=0.00, editorial_penalty=0.5, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=79.0, section_fit=80.0, core=77.0, summary=88.0, missed=76.0, noise=79.0
- Summary: 카드 수는 전 섹션 5개를 채웠지만, 기사 고르기 자체는 95점대와 거리가 있다. 공급은 홍보성 양파 기사에 코어를 준 점이 가장 큰 감점 요인이고, 정책은 지역 생활물가 기사가 섹션 취지에 약하다. 유통은 온라인 도매시장 MOU는 좋지만 나머지 다수가 출하식·판촉전 중심의 로컬 홍보성 기사여서 운영·물류 관점이 약해졌다. 병해충은 화상병 중심 축은 맞췄지만 더 강한 확산/현장 피해 기사들이 후보군에 있었는데 코어·상단 반영이 약했다. 요약은 대체로 쓸 만하나, 원문 선택이 약해 전체 편집 완성도는 ‘사용 가능하나 수정 필요’ 수준이다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 소비 독려성 기관 홍보에 가깝고 수급 핵심 기사로 약하다.
- [high] missed_opportunity: 과잉 양파 '수매'·부족 계란 '수입'…정부 "6~7월 물가 안정 총력" - 가장 직접적인 수급 대응 기사인데 공급 섹션에서 빠졌다.
- [medium] wrong_fit: 괴산군 원원종 감자 생산 목표 초과 달성 - 지역 성과성 보드 기사로 당일 수급 이슈성과 약하다.
- [medium] wrong_fit: 계란 등 인천도 생활물가 등락...고추장·배추·오이 내린 곳도 - 지역 물가 스케치 수준으로 중앙 정책 섹션 적합도가 낮다.
- [medium] duplicate_angle: 강원농협·농협공판장, 온라인 도매시장 활성화 앞장 / 강원 농산물 온라인 도매시장 경쟁력 키운다 - 동일 사안 중복 편입으로 슬롯을 낭비했다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
