## Daily Eval (2026-06-12)
- Overall: **96.26** (pass)
- Operational: **96.96**
- Reader quality: **96.96** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **96.26** (needs_iteration, editorial_below_target_bounded_penalty; editorial=88.0, operational=97.0)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=84.6, section_fit=91.7, core=94.1, commodity=92.0
- Briefing cards: 20 / Commodity cards: 14
- Sections: supply:5/5 raw=203, policy:5/5 raw=73, dist:5/5 raw=45, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.65, fresh_72h=1.00, fit_avg=3.68, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=6, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **88.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=86.0, section_fit=87.0, core=90.0, summary=92.0, missed=84.0, noise=86.0
- Summary: 전반적으로 5개 섹션 수를 맞추고 핵심 현안인 양파 수급·여름배추·과수화상병·도매시장 물류를 담아 기본 편집력은 좋다. 다만 공급과 정책에서 양파 이슈가 중복적으로 퍼져 있고, 공급 섹션에 지역 농협성 지원 기사와 매실 시황 기사가 다소 약하게 섞였다. 유통은 물류·공판장·저온유통을 포함해 방향은 맞지만 ‘다올찬수박’ 같은 출하 홍보성 카드가 너무 앞에 왔다. 병해충은 화상병 축을 잘 잡았으나 하단 카드 2장은 검역 고시·지역 방제 안내로 긴급도와 전국성이 상대적으로 떨어진다. 원자료 풀을 보면 더 날카로운 대체나 재배치가 가능해 95점대는 어렵다.
- [medium] duplication: 양파 산업 위기 해법 찾는다 - 공급 섹션 양파 기사들과 주제가 크게 겹친다.
- [medium] weak_tail: 진주문산농협, 못난이 매실 가공용 수매 지원 나선다 - 지역 지원성 기사로 전국 수급 핵심성은 약하다.
- [medium] weak_tail: 광양 매실 생산량 급증... 가격 은 전년보다 하락 조짐 - 지역 시황 기사로 파급력은 제한적이다.
- [medium] section_fit: 고당도 ‘다올찬수박’ 본격 출하 - 출하 소식은 맞지만 판촉성 색채가 강하다.
- [medium] missed_opportunity: “농산물 판매, 디지털 전환해야”…전남농협, 농협몰 설명회 열어 - 온라인 판매 운영 이슈가 있는데 선택되지 않았다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
