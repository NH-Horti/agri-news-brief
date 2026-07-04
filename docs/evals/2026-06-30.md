## Daily Eval (2026-06-30)
- Overall: **94.97** (pass)
- Operational: **95.67**
- Reader quality: **95.67** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **94.97** (needs_iteration, editorial_below_target_bounded_penalty; editorial=88.0, operational=95.7)
- Scores: completeness=100.0, diversity=100.0, summary=94.0, freshness=100.0, retrieval=73.7, section_fit=100.0, core=90.5, commodity=88.0
- Briefing cards: 20 / Commodity cards: 25
- Sections: supply:5/5 raw=193, policy:5/5 raw=81, dist:5/5 raw=40, pest:5/5 raw=12
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=4.33, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=6, commodity_active_today=11, commodity_active_today_unlinked=5, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.83, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **88.00** (target 95, needs_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=87.0, section_fit=88.0, core=86.0, summary=78.0, missed=84.0, noise=82.0
- Summary: 분량과 신선도는 목표를 충족했고, 공급·가격 급락, 양파 수급, 도매시장 출하예측, 가락시장 휴업, 과수화상병 등 핵심 이슈는 대체로 포착했다. 다만 유통 섹션에 정책·산업진단성 화훼 기사가 들어가고, 정책·유통·병해충 후반부에 회의·MOU·주간 메모성 filler가 섞였다. 원자료에 더 구체적인 시장운영·물류·현장피해 후보가 보이는데 일부 약한 꼬리 카드가 이를 밀어낸 점, 몇몇 요약이 스크랩/AI 안내 문구나 잘린 문장으로 남은 점 때문에 95점권은 아니다.
- [major] wrong_section: 화훼 산업, 이대로면 사라진다 - 유통·물류·판매채널보다 산업 구조와 소비문화 정책 토론에 가까워 dist 적합도가 낮다.
- [major] weak_tail: 농경연· 농식품부 , 주요 농정 현안 대응 협력 강화 - 정책연구협의회 개최 중심의 기관 동정으로 독자가 얻을 실행 정보가 약하다.
- [medium] weak_core: 토마토 선별·포장, 로봇이 다 해줍니다 - APC 자동화 소재는 좋지만 기사 본문이 사진설명 수준이라 core 카드로는 정보 밀도가 낮다.
- [medium] promotional_filler: 대아청과·애월 농협 , 제주산 농산물 유통 활성화 '맞손' - 간담회·협력 홍보 성격이 강하고 실제 물량, 가격, 운영 변화가 제한적이다.
- [medium] duplication: 해남군 '고온다습 장마철 '고추 병해충 예방 당부 - 경북 고추 탄저병·세균성점무늬병 카드와 병해충 테마가 겹치며 지역 안내 성격이 강하다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: policy, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
