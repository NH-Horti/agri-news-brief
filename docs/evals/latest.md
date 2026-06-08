## Daily Eval (2026-06-08)
- Overall: **82.00** (warn)
- Operational: **95.81**
- Quality gate: **82.00** (needs_iteration, editorial_below_target; editorial=82.0, operational=95.8)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=98.3, retrieval=85.0, section_fit=100.0, core=95.4, commodity=98.4
- Briefing cards: 19 / Commodity cards: 55
- Sections: supply:5/5 raw=230, policy:5/5 raw=155, dist:4/5 raw=92, pest:5/5 raw=75
- Metrics: title_unique=1.00, domain_diversity=0.84, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=4.32, false_positive=0.00, weak_core=0.14, editorial_penalty=0.5, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=79.0, section_fit=81.0, core=80.0, summary=86.0, missed=77.0, noise=83.0
- Summary: 양파 수급과 과수화상병 등 핵심 이슈는 잡았지만, 공급·정책·유통 섹션에서 같은 양파 축을 과도하게 반복했고, 공급/정책에 들어간 ‘특별성과 포상’은 비핵심성·섹션 부적합성이 큽니다. 유통은 가락시장 휴업 이슈를 살린 점은 좋지만 5장 목표를 채우지 못했고, 온라인도매시장·수출/물류 이슈 등 더 나은 후보를 놓쳤습니다. 전반적으로 읽히는 브리프는 됐으나, 기사 선택 자체는 엄격 기준에서 상위권 점수까지는 어렵습니다.
- [high] wrong_section: 농식품부 , 특별성과 공무원 11명 포상…배추 수급관리·쌀대여 선정 - 공무원 포상 소식은 공급 이슈 카드로 보기 어렵다.
- [high] noise: 농식품부, 특별성과 공무원 11명에 4,500만 원 포상금 지급 - 정책 영향보다 내부 포상 이벤트 성격이 강하다.
- [high] duplication: 함양 양파 수출/수매비축 관련 3건 동시 편성 - 같은 양파 수급 대응을 유사 각도로 반복해 지면 효율이 낮다.
- [medium] cross_section_overlap: 정부·농협, 양파 값 지지 ‘총력’…수출확대 박차 - 내용이 공급 섹션 양파 기사들과 실질적으로 겹친다.
- [medium] underfill: 유통 섹션 4장 편성 - 원시 후보가 충분한데 5장 목표를 채우지 못했다.

### Improvement Hints
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
