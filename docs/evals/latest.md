## Daily Eval (2026-06-08)
- Overall: **82.00** (warn)
- Operational: **96.26**
- Quality gate: **82.00** (needs_iteration, editorial_below_target; editorial=82.0, operational=96.3)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=98.3, retrieval=90.6, section_fit=100.0, core=95.4, commodity=98.4
- Briefing cards: 19 / Commodity cards: 54
- Sections: supply:5/5 raw=230, policy:5/5 raw=154, dist:4/5 raw=93, pest:5/5 raw=77
- Metrics: title_unique=1.00, domain_diversity=0.84, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=4.32, false_positive=0.00, weak_core=0.14, editorial_penalty=0.5, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=78.0, section_fit=76.0, core=74.0, summary=88.0, missed=80.0, noise=79.0
- Summary: 전반적으로 시의성 있는 농정·수급 이슈를 많이 담았지만, 양파 이슈 중복이 과하고 공무원 포상 기사를 공급·정책·유통에 걸쳐 재사용한 점이 치명적입니다. 특히 공급 섹션의 코어가 잘못 잡혔고, 유통 섹션은 가락시장 휴업 같은 강한 운영 이슈가 있는데도 약한 수박 가격 기사와 비유통성 기사로 구성력이 흔들렸습니다. 병해충은 과수화상병 확산을 잘 포착했지만 중복도가 높습니다. 섹션 수는 대체로 채웠으나 dist가 4건에 그쳐, 광범위한 fallback가 있는 만큼 90점대 중후반 평가는 어렵습니다.
- [high] wrong_section: 농식품부 , 특별성과 공무원 11명 포상…배추 수급관리·쌀대여 선정 - 공급 동향이 아니라 내부 포상 기사다.
- [high] duplicate_theme: 함양군, 함양농협과 햇 양파 첫 대만 수출로 수급 안정 총력 - 같은 양파 수출·수급 기사가 섹션 내 3건 겹친다.
- [high] cross_section_duplication: “성과 낸 공무원 보상”…농식품부, 특별성과 11명에 4500만원 포상 - 정책성 포상 기사를 유통 섹션에 넣어 성격이 어긋난다.
- [high] weak_core: 언론 장식한 '금 수박 '…생산·유통 현장엔 '한숨만' - 유통 핵심이라기보다 가격 해설 기사로 운영·물류 강도가 약하다.
- [medium] missed_opportunity: 가락 쉬자 전국 도매시장 들썩…휴업 도미노 오나 - 가장 강한 전국 유통 운영 이슈인데 코어가 아니었다.

### Improvement Hints
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
