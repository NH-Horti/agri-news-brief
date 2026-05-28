## Daily Eval (2026-05-28)
- Overall: **84.00** (warn)
- Operational: **95.83**
- Quality gate: **84.00** (needs_iteration, editorial_below_target; editorial=84.0, operational=95.8)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=100.0, core=100.0, commodity=96.6
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=144, policy:5/5 raw=91, dist:5/5 raw=30, pest:5/5 raw=55
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=5.09, false_positive=0.00, weak_core=0.00, editorial_penalty=2.9, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=81.0, section_fit=82.0, core=78.0, summary=90.0, missed=79.0, noise=80.0
- Summary: 형식과 개수는 채웠지만, 편집 판단은 목표 95점에 못 미칩니다. 공급 섹션의 1번 코어가 홍보성 지역 기사여서 핵심성·전국성이 약했고, 정책 섹션은 정부 수급점검회의 기사 중복과 인천 지역 생활물가 같은 비핵심 로컬 기사로 밀도가 떨어졌습니다. 유통은 온라인 도매시장 코어는 좋았지만 나머지 다수가 출하식·판촉전 성격이라 운영 이슈 중심성이 약했습니다. 병해충은 과수화상병 축을 잡은 점은 맞지만, 위기단계 상향·신규 발생 같은 더 직접적인 대응 기사 비중을 더 높였어야 합니다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 지역 소비홍보성 기사로 전국 수급 핵심도가 낮다.
- [high] missed_opportunity: 과잉 양파 '수매'·부족 계란 '수입'…정부 "6~7월 물가 안정 총력" - 당일 가장 직접적인 수급 대응 기사인데 공급 섹션에 반영 안 됨.
- [medium] duplication: 농축산물 물가, 맞춤형으로 대응 / 농산물 가격은 내리고 축산물은 오르고… - 같은 정부 점검회의를 반복해 정보 효율이 낮다.
- [medium] wrong_fit: 계란 등 인천도 생활물가 등락...고추장·배추·오이 내린 곳도 - 지역 물가 스케치로 중앙 정책 섹션 적합성이 낮다.
- [medium] weak_selection: 완주 삼례 농협 , 명품 흑피수박 ‘블랙위너’ 본격 출하 - 출하식·브랜드 홍보 성격이 강해 유통 운영 기사로는 약하다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
