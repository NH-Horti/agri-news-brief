## Daily Eval (2026-07-03)
- Overall: **95.16** (pass)
- Operational: **96.26**
- Reader quality: **96.26** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **95.16** (needs_iteration, editorial_below_target_bounded_penalty; editorial=84.0, operational=96.3)
- Scores: completeness=100.0, diversity=100.0, summary=85.0, freshness=100.0, retrieval=83.8, section_fit=100.0, core=100.0, commodity=99.1
- Briefing cards: 20 / Commodity cards: 42
- Sections: supply:5/5 raw=189, policy:5/5 raw=191, dist:5/5 raw=93, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.85, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=5.09, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=10, commodity_active_today=14, commodity_active_today_unlinked=4, commodity_coverage=0.30, commodity_strict_link=0.90, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=83.0, section_fit=82.0, core=79.0, summary=72.0, missed=77.0, noise=73.0
- Summary: 분량은 4개 섹션 모두 5건으로 충족했고, 공급 섹션은 배추·강원 여름작물·양배추 폭락 등 핵심 수급 이슈를 잘 잡았다. 다만 정책 섹션은 6월 물가/최고가격제 기사 중복이 과하고, 한 카드의 요약이 본문이 아닌 공유 UI로 깨져 독자 효용을 크게 떨어뜨린다. 유통 섹션은 산지경매·도매시장 휴업은 적합하지만 정책성 할인 기사와 교육 행사성 기사가 핵심 유통 뉴스보다 앞섰다. 병해충 섹션은 화상병 대응은 적절하나 단감 탄저병·고추 탄저병·애호박 뿌리혹병 같은 더 구체적인 작물 병해 리스크를 일부 놓쳤다.
- [major] bad_summary: 정부 “최고 가격 제 없었다면 6월 물가 상승률 3.2% 아닌 3.6%” - 요약이 공유·프린트 UI 문구 반복으로 기사 내용을 전달하지 못한다.
- [major] duplicate_theme: 정부 “최고 가격 제 없었다면… / 24% 뛴 유가發… / [이로운체크] 6월 물가… - 세 카드가 같은 6월 물가와 정부 물가대책을 반복한다.
- [moderate] weak_core_pick: 정부, 계란 공급 늘리고 농축산물 할인 확대 - 핵심 정책 이슈지만 출처·요약 품질이 약하고 더 선명한 전국 단위 후보가 있었다.
- [moderate] wrong_section_or_priority: 정부, 농축산물 할인에 3000억원 투입…농할상품권 월 200억원 발행 - 판매채널 요소는 있으나 본질은 물가정책 기사라 유통 핵심 카드로는 약하다.
- [moderate] promotional_filler: 청년 양돈농가, 공판장 서 축산유통 배웠다 - 교육 행사성 기사로 실제 물류·시장운영·출하 변화 신호가 약하다.

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 리콜 시드 결손이 보입니다: supply, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
