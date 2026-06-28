## Daily Eval (2026-06-22)
- Overall: **96.58** (pass)
- Operational: **97.88**
- Reader quality: **97.88** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **96.58** (needs_iteration, editorial_below_target_bounded_penalty; editorial=82.0, operational=97.9)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=95.7, retrieval=88.8, section_fit=100.0, core=92.9, commodity=97.5
- Briefing cards: 20 / Commodity cards: 47
- Sections: supply:5/5 raw=238, policy:5/5 raw=242, dist:5/5 raw=70, pest:5/5 raw=82
- Metrics: title_unique=1.00, domain_diversity=0.80, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.87, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=13, commodity_active_today=17, commodity_active_today_unlinked=4, commodity_coverage=0.39, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.54, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=83.0, core=84.0, summary=76.0, missed=78.0, noise=81.0
- Summary: 전반적으로 섹션 수는 잘 채웠고 공급·정책의 핵심 의제도 대체로 잡았지만, 공급 섹션의 중복·로컬 호소성 기사 과다, 유통 섹션의 전국 운영기사 미반영, 병해충 섹션의 약한 꼬리 기사 때문에 편집 완성도는 90점대까지 보기 어렵다. 특히 공급은 양파·마늘 하락 기사들이 유사하게 겹쳤고, 유통은 가락시장 배추 경매시간 조정 같은 실제 운영 변화 기사가 더 앞서야 했다.
- [high] duplication: 생장불량 마늘·과잉생산 양파 …주산지 경남 농민 '시름' / 생산비도 못 건지는 남해 마늘 가격…농민들 "가격안정" 요구 - 양파·마늘 가격난을 지역 단위로 비슷하게 반복했다.
- [medium] filler: 경북도의회, 농산물 가격 폭락 '선제적 대응' 촉구 - 지방의회 발언성 기사로 정보 밀도가 낮다.
- [medium] filler: 양파값 폭락에 가락시장 도매법인 3사 '3억원' 투입 - 소비촉진 이벤트 성격이 강해 핵심 수급 기사로는 약하다.
- [high] missed_opportunity: 가락시장, 여름철 배추 경매시간 1시간 앞당긴다 - 실제 도매시장 운영 변화인데 선택본에서 비핵심 후순위 처리됐다.
- [medium] section_fit: 영천 스마트 APC 가동…AI 스펙트럼 선별로 '공동출하 경쟁력' 키운다 - 유통 섹션 적합성은 있으나 지역 홍보성 톤이 강하다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
