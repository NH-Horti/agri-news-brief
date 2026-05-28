## Daily Eval (2026-05-28)
- Overall: **83.00** (warn)
- Operational: **97.78**
- Quality gate: **83.00** (needs_iteration, editorial_below_target; editorial=83.0, operational=97.8)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=100.0, core=100.0, commodity=96.6
- Briefing cards: 20 / Commodity cards: 38
- Sections: supply:5/5 raw=142, policy:5/5 raw=89, dist:5/5 raw=31, pest:5/5 raw=52
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=5.15, false_positive=0.00, weak_core=0.00, editorial_penalty=0.9, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=82.0, core=78.0, summary=90.0, missed=79.0, noise=77.0
- Summary: 섹션 수는 모두 채웠지만, 편집 품질은 목표 95에 못 미칩니다. 공급 섹션의 1번 코어가 소비홍보성 양파 기사여서 톱픽으로 약하고, 정책은 정부 수급점검 기사와 가격안정제 기사 축이 맞지만 지역 생활물가 기사와 유사 정부발 기사 중복이 섞였습니다. 유통은 온라인도매시장 기사 선택은 좋았으나 동일 사안 중복과 판촉·출하식 비중이 높아 운영·물류성 밀도가 떨어집니다. 병해충은 과수화상병 집중 편성 자체는 맞지만, 전국 확산·위기단계 격상 같은 더 강한 스트레이트를 충분히 전면화하지 못했습니다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 소비홍보성 지역 기사로 공급 톱픽 가치가 낮다.
- [high] missed_opportunity: 과잉 양파 '수매'·부족 계란 '수입'…정부 "6~7월 물가 안정 총력" - 같은 날 전국 수급대응 기사인데 공급 섹션에서 빠졌다.
- [medium] wrong_fit: 계란 등 인천도 생활물가 등락...고추장·배추·오이 내린 곳도 - 지역 물가 스케치로 중앙 정책 섹션 적합도가 낮다.
- [high] duplication: 강원농협·농협공판장, 온라인 도매시장 활성화 앞장 / 강원 농산물 온라인 도매시장 경쟁력 키운다 - 동일 협약 사안을 중복 수록했다.
- [medium] promotional_filler: 완주 삼례 농협 , 명품 흑피수박 ‘블랙위너’ 본격 출하 - 출하식·품종 홍보 성격이 강하다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
