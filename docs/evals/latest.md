## Daily Eval (2026-05-28)
- Overall: **72.00** (warn)
- Operational: **95.83**
- Quality gate: **72.00** (needs_major_iteration, editorial_below_target; editorial=72.0, operational=95.8)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=100.0, core=100.0, commodity=96.6
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=142, policy:5/5 raw=91, dist:5/5 raw=30, pest:5/5 raw=51
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=5.09, false_positive=0.00, weak_core=0.00, editorial_penalty=2.9, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **72.00** (target 95, needs_major_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=68.0, section_fit=70.0, core=66.0, summary=84.0, missed=62.0, noise=60.0
- Summary: 형식과 수량은 맞췄지만, 기사 선택의 편집 판단은 약하다. 공급 섹션은 지역 홍보성 양파 기사와 씨감자 실적성 기사까지 넣어 핵심 수급 이슈를 흐렸고, 정책 섹션은 중앙 정책·제도 기사와 중복되는 생활물가 지역 단신이 노이즈다. 유통 섹션은 온라인 도매시장 MOU는 좋았지만 동일 사안을 중복 채우고 판촉·출하식 비중이 높다. 병해충 섹션은 과수화상병 전국 확산 국면을 대체로 잡았으나 가장 강한 발생·격상 기사보다 계도성 기사에 코어를 준 점이 아쉽다.
- [high] wrong_priority: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 소비 촉진 홍보성 지역 기사인데 코어로 과대선정.
- [high] filler: 괴산군 원원종 감자 생산 목표 초과 달성 - 지역 기관 실적성 기사로 당일 핵심 수급 흐름과 거리 큼.
- [medium] duplication: 농산물 물가, 맞춤형으로 대응 / 농산물 가격은 내리고 축산물은 오르고… - 같은 정부 점검회의 재탕으로 정보 증분이 작음.
- [high] wrong_section: 계란 등 인천도 생활물가 등락...고추장·배추·오이 내린 곳도 - 지역 장바구니 단신은 중앙 정책 섹션과 맞지 않음.
- [medium] duplication: 강원농협·농협공판장, 온라인 도매시장 활성화 앞장 / 강원 농산물 온라인 도매시장 경쟁력 키운다 - 동일 MOU를 사실상 중복 채택.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
