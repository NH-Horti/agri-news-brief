## Daily Eval (2026-05-28)
- Overall: **82.00** (warn)
- Operational: **95.83**
- Quality gate: **82.00** (needs_iteration, editorial_below_target; editorial=82.0, operational=95.8)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=100.0, core=100.0, commodity=96.6
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=144, policy:5/5 raw=89, dist:5/5 raw=30, pest:5/5 raw=51
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=5.04, false_positive=0.00, weak_core=0.00, editorial_penalty=2.9, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=79.0, core=76.0, summary=88.0, missed=83.0, noise=78.0
- Summary: 카드 수는 목표를 채웠지만, 실제 편집 품질은 그보다 낮다. 공급 섹션의 1번 코어가 소비촉진 홍보성 기사라 약하고, 정책은 생활물가 지역 단신과 본문 깨진 저품질 기사까지 넣어 밀도가 떨어진다. 유통은 온라인도매시장 기사는 좋지만 판촉·출하식 비중이 높아 운영성 기사 선호에 못 미쳤다. 병해충은 화상병 확산 이슈를 중심에 둔 점은 맞지만 더 강한 전국 확산·신규 발생 후보를 일부 비핵심으로 처리했다. 전반적으로 ‘형식상 만점, 편집상 보통 이상’ 수준이다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 소비촉진 홍보성 기사로 수급 핵심 기사로는 약함.
- [high] missed_opportunity: 과잉 양파 '수매'·부족 계란 '수입'…정부 "6~7월 물가 안정 총력" - 같은 날 전국 수급 대응을 포괄한 더 강한 후보를 놓침.
- [medium] wrong_weight: 계란 등 인천도 생활물가 등락...고추장·배추·오이 내린 곳도 - 지역 생활물가 단신은 전국 정책 섹션에서 우선순위 낮음.
- [high] low_quality_source: 양파값 급락·계란값 고공행진…정부, 수급 안정·할인지원 총력 - 본문 확인 불가 수준의 깨진 기사로 정보 신뢰도 낮음.
- [medium] missed_opportunity: 완주 삼례 농협 , 명품 흑피수박 ‘블랙위너’ 본격 출하 - 출하식 기사보다 유통제도·물류 기사 가치가 낮음.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
