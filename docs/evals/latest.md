## Daily Eval (2026-06-12)
- Overall: **96.28** (pass)
- Operational: **97.18**
- Reader quality: **97.18** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **96.28** (needs_iteration, editorial_below_target_bounded_penalty; editorial=86.0, operational=97.2)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=84.6, section_fit=91.7, core=94.4, commodity=96.1
- Briefing cards: 20 / Commodity cards: 14
- Sections: supply:5/5 raw=203, policy:5/5 raw=75, dist:5/5 raw=43, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=3.68, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=7, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=86.0, core=88.0, summary=92.0, missed=82.0, noise=83.0
- Summary: 전반적으로 당일 핵심 이슈는 잘 잡았고 4개 섹션 모두 5건을 채운 점은 좋다. 다만 공급·정책에서 양파 이슈가 중복적으로 반복되고, 공급의 말미와 유통의 일부 카드는 지역성·행사성 성격이 강해 더 나은 운영·유통 기사로 교체할 여지가 보인다. 병해충은 화상병을 중심축으로 잡은 판단은 적절했지만, 같은 현장점검 축의 변주가 많아 후반 카드의 밀도는 다소 떨어진다. publish급에 가깝지는 않고, 분명한 편집 보정이 필요한 브리핑이다.
- [high] duplication: 양파 값 역전 해법 찾고 수출길 넓히고 - 정책 섹션의 양파 토론회 기사와 사실상 같은 축이다.
- [medium] section_fit: 양파산업 위기 해법 찾는다 - 수급·산업 이슈이지만 공급 기사와의 구분이 약하다.
- [high] filler: 진주문산농협, 못난이 매실 가공용 수매 지원 나선다 - 지역 지원성 기사로 전국성·핵심성이 약하다.
- [medium] section_fit: 고당도 ‘다올찬수박’ 본격 출하 - 출하 소식 위주로 물류·시장운영 정보가 제한적이다.
- [medium] filler: 청도 농협공판장 일제 개장…"농업인 소득증대 최선" - 개장 행사 성격이 강하고 운영 변화 정보가 얕다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
