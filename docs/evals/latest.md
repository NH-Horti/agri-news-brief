## Daily Eval (2026-06-22)
- Overall: **83.00** (warn)
- Operational: **96.19**
- Reader quality: **96.19** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **83.00** (needs_iteration, editorial_blocking_issue; editorial=83.0, operational=96.2)
- Scores: completeness=100.0, diversity=95.0, summary=100.0, freshness=91.4, retrieval=88.8, section_fit=100.0, core=90.2, commodity=97.5
- Briefing cards: 20 / Commodity cards: 47
- Sections: supply:5/5 raw=242, policy:5/5 raw=241, dist:5/5 raw=72, pest:5/5 raw=82
- Metrics: title_unique=1.00, domain_diversity=0.65, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=5.33, false_positive=0.00, hard_reader_issues=0, weak_core=0.17, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=13, commodity_active_today=17, commodity_active_today_unlinked=4, commodity_coverage=0.39, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.54, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=80.0, core=84.0, summary=92.0, missed=78.0, noise=79.0
- Summary: 구색은 5×4를 맞췄고 일부 핵심 기사 선택은 괜찮지만, 공급·정책에서 토론회/의원발 지역성 기사와 중복 주제 비중이 높고, 유통은 운영 기사보다 농협 성과홍보성 카드가 중심을 차지해 편집 완성도가 떨어진다. 병해충은 과수화상병 축을 잡았으나 하위 카드 2건이 약하다. 원시 후보군이 충분했기 때문에 더 강한 전국 단위·운영형 기사로 교체할 여지가 분명했다.
- [high] wrong_section: 송옥주 의원, 농산물 가격안정제 정책토론회 개최 - 정책·행사성 기사로 공급 섹션 부적합
- [high] weak_fit: 남도종 마늘 농가 “ 수급 조절 기준 현실화 시급” - 핵심은 가이드라인·기준 개편 요구로 정책 성격
- [medium] promotional_filler: [판매 농협 이 간다] 신북 농협 , 농산물 온라인 매출액 2년 새 3배 ‘껑충’ - 농협 성공사례 성격이 강해 유통 현안성은 약함
- [medium] promotional_filler: 진주시, 청양고추 가공품 북미 첫 수출 …한인 유통망 소비자 접점 확보 - 지자체 첫 수출 홍보성 지역 기사
- [medium] weak_core: 공선회·APC 운영 활성화…판매사업 날개 - 유통 운영 사례지만 농협 홍보 톤이 강함

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
