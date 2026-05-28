## Daily Eval (2026-05-28)
- Overall: **82.00** (warn)
- Operational: **95.97**
- Quality gate: **82.00** (needs_iteration, editorial_below_target; editorial=82.0, operational=96.0)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=100.0, core=100.0, commodity=97.4
- Briefing cards: 20 / Commodity cards: 38
- Sections: supply:5/5 raw=143, policy:5/5 raw=89, dist:5/5 raw=31, pest:5/5 raw=52
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=5.12, false_positive=0.00, weak_core=0.00, editorial_penalty=2.8, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=79.0, core=76.0, summary=89.0, missed=78.0, noise=74.0
- Summary: 구색은 5×4로 맞췄지만, 실제 편집 선택은 목표점수 95에 못 미친다. 공급은 가장 약하다. 정부 수급점검회의 기반의 더 큰 전국 이슈가 raw pool에 충분했는데, 홍보성 양파 소비 기사와 씨감자 지역 성과물이 들어와 핵심감이 떨어졌다. 정책은 계란 할인 확대와 가격안정제 토론회는 괜찮지만, 인천 생활물가와 중복성 강한 정부 해명/재탕 기사가 꼬리에서 품질을 깎았다. 유통은 온라인 도매시장 MOU는 적합하나 수도권 판촉전·출하식류 비중이 높아 운영·물류감이 약하다. 병해충은 과수화상병 중심 편성 방향은 맞지만, 가장 강한 ‘공주 첫 발생+경계 격상’ 단신을 비핵심으로 두고 지역 약제지원·기업 특허 기사를 섞은 점이 아쉽다. 요약문 자체는 대체로 유용하지만, 기사 선별의 강약 조절과 섹션 정밀도가 부족하다.
- [high] missed_opportunity: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 홍보성 소비촉진 기사인데 전국 수급점검회의 기사가 더 강했다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 코어로 두기엔 정책·수급 정보량이 약하다.
- [medium] noise: 괴산군 원원종 감자 생산 목표 초과 달성 - 지역 성과성 보드 기사로 당일 전국 수급 이슈 대비 우선순위 낮다.
- [medium] wrong_fit: 계란 등 인천도 생활물가 등락...고추장·배추·오이 내린 곳도 - 지역 물가 스케치에 가까워 중앙 정책 섹션 적합도가 낮다.
- [medium] duplicate_theme: 양파값 급락·계란값 고공행진…정부, 수급 안정·할인지원 총력 - 동일 회의 재가공 기사로 새 정보가 적고 품질도 낮다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
