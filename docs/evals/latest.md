## Daily Eval (2026-05-28)
- Overall: **98.32** (pass)
- Operational: **98.32**
- Quality gate: **98.32** (target_met, all_targets_met; editorial=95.0, operational=98.3)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=100.0, core=100.0, commodity=97.4
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=144, policy:5/5 raw=89, dist:5/5 raw=31, pest:5/5 raw=52
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=5.11, false_positive=0.00, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Section count gate: 100.0 (target_met)
- Score calibration: 81.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=78.0, section_fit=80.0, core=72.0, summary=86.0, missed=79.0, noise=74.0
- Summary: 형식은 갖췄지만 기사 고르기가 약하다. 공급 섹션의 1번 코어가 소비홍보성 지방 기사여서 가장 큰 감점 요인이고, 정책은 같은 정부 수급회의 계열을 중복 반영하면서 지역 생활물가 기사와 인코딩 깨진 기사를 넣어 밀도가 떨어졌다. 유통은 온라인도매시장 기사 선택은 괜찮지만 판촉·출하식 비중이 높아 운영성 뉴스가 부족하다. 병해충은 화상병 중심 축은 맞았으나 이미 확산·경계 격상 국면에서 더 강한 발생/위기 기사들을 앞세울 수 있었다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 소비홍보성 지방 기사로 공급 핵심 이슈 대표성이 약함.
- [high] missed_opportunity: 과잉 양파 '수매'·부족 계란 '수입'…정부 "6~7월 물가 안정 총력" - 당일 전국 수급대응 핵심 기사인데 공급 섹션에서 빠짐.
- [medium] duplication: KREI 토론회 + [단독] 정부, 농산물 과잉생산 막는다 - 둘 다 가격안정제 한 주제를 반복해 정책 면 폭이 좁아짐.
- [medium] wrong_fit: 계란 등 인천도 생활물가 등락...고추장·배추·오이 내린 곳도 - 지역 장바구니 기사로 중앙 정책 섹션 적합성이 낮음.
- [medium] quality_risk: 양파값 급락·계란값 고공행진…정부, 수급 안정·할인지원 총력 - 본문 인코딩 문제로 신뢰성과 요약 근거가 약함.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
