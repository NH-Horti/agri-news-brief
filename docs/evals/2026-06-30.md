## Daily Eval (2026-06-30)
- Overall: **94.77** (pass)
- Operational: **95.67**
- Reader quality: **95.67** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **94.77** (needs_iteration, editorial_below_target_bounded_penalty; editorial=86.0, operational=95.7)
- Scores: completeness=100.0, diversity=100.0, summary=94.0, freshness=100.0, retrieval=73.7, section_fit=100.0, core=90.5, commodity=88.0
- Briefing cards: 20 / Commodity cards: 25
- Sections: supply:5/5 raw=193, policy:5/5 raw=81, dist:5/5 raw=40, pest:5/5 raw=12
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=4.33, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=6, commodity_active_today=11, commodity_active_today_unlinked=5, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.83, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.00** (target 95, needs_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=86.0, section_fit=84.0, core=85.0, summary=78.0, missed=82.0, noise=80.0
- Summary: 분량은 모든 섹션 5건으로 충족했고, 공급·정책의 핵심 수급 이슈는 대체로 잘 잡았다. 다만 유통 섹션에 화훼 산업 위기처럼 유통 운영성이 약한 기사가 들어갔고, 병해충 섹션은 고추 병해충 고지 중복과 generic 농사메모로 인해 더 뉴스가치 있는 사과나무 집단 고사·원인불명 후보를 놓쳤다. 일부 요약은 원문 UI/AI 안내 문구나 방송 대본 머리말이 섞여 독자용 브리핑 품질을 낮춘다.
- [major] wrong_section: 화훼 산업, 이대로면 사라진다 - 화훼 생산기반·소비문화·정책 토론 성격으로 유통·물류·시장운영 기사와 거리가 있다.
- [major] missed_candidate: 사과 나무 무더기로 죽었는데 원인 불명?…경찰 수사까지 - 사과 과수원 100여 그루 피해와 원인 조사라는 현장성 높은 병해·생육 리스크 후보를 누락했다.
- [medium] duplication: 해남군 '고온다습 장마철 '고추 병해충 예방 당부 - 경북 고추 탄저병·세균성점무늬병 확산 우려 기사와 주제가 겹치고 지역 안내성도 강하다.
- [medium] weak_tail: [주간농사메모] 병해충 발생 여부 수시 예찰 - 여러 작목 일반 관리요령을 나열한 정례 메모라 당일 뉴스성과 긴급성이 낮다.
- [medium] promotional_or_event_filler: 농경연· 농식품부 , 주요 농정 현안 대응 협력 강화 - 정책연구협의회 개최 소식 중심으로 독자에게 필요한 구체 정책 변화가 약하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: policy, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
