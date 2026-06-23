## Daily Eval (2026-06-24)
- Overall: **94.05** (pass)
- Operational: **96.25**
- Reader quality: **95.35** (clear; penalty=0.9, cap=100.0, reasons=clear)
- Quality gate: **94.05** (needs_iteration, editorial_below_target_bounded_penalty; editorial=82.0, operational=96.2)
- Scores: completeness=100.0, diversity=90.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=100.0, commodity=92.0
- Briefing cards: 20 / Commodity cards: 26
- Sections: supply:5/5 raw=216, policy:5/5 raw=103, dist:5/5 raw=64, pest:5/5 raw=36
- Metrics: title_unique=1.00, domain_diversity=0.60, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.88, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.5, commodity_weak=0.00, commodity_items=9, commodity_active_today=12, commodity_active_today_unlinked=3, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=83.0, core=84.0, summary=91.0, missed=76.0, noise=78.0
- Summary: 구색은 5×4로 맞췄고 핵심 주제도 대체로 맞았지만, 실제 기사 선택의 질은 목표 95점에 못 미친다. 공급은 양파 하락 이슈를 과도하게 중복 채웠고, 정책은 더 강한 정부 수급점검 기사를 두고 계란 소비물가성 기사 2건을 실었다. 유통은 직거래 상담회 중복과 복숭아 첫 출하 같은 약한 현장성 카드가 섞였고, 병해충은 화상병 축은 괜찮지만 지원성 단감 약제 기사가 더 강한 화상병 확산·신고기피 후보를 밀어냈다. 요약문은 전반적으로 유용하나 기사 배치 자체가 아쉬워 편집 완성도는 중상 수준이다.
- [high] missed_better_candidate: 축산물 가격 '고공행진'…정부, 비축물량 방출·할인지원 - 가장 강한 정부 수급대응 기사인데 미선정.
- [high] duplication: "계란프라이도 사치?"... 달걀 10구 첫 5000원 돌파 / 특란 10구 5000원 넘고 정부 수입 달걀도 오픈런 - 같은 계란 가격 급등 이슈를 유사 각도로 중복.
- [high] duplication: 전북도 양파 대책 / [사실은 이렇습니다] 양파 수급안정 / 경북협의회 특판 / 함양 수매가 인하 - 양파 하락 대응 기사 비중이 과도해 공급 섹션 다양성 저하.
- [medium] wrong_weight: 이천 장호원농협, ‘햇사레 복숭아’ 첫 출하 - 첫 출하 공지 성격이 강해 유통 운영 이슈로는 약함.
- [medium] duplication: "산지-소비지 연결로 물가 안정 도움" / 농산물 생산자와 구매사 한자리에 직거래 판로 넓힌다 - 동일 행사 중복 채택으로 슬롯 낭비.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
