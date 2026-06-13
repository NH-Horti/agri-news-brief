## Daily Eval (2026-06-12)
- Overall: **84.00** (warn)
- Operational: **96.29**
- Reader quality: **95.39** (clear; penalty=0.9, cap=100.0, reasons=clear)
- Quality gate: **84.00** (needs_iteration, editorial_below_target; editorial=84.0, operational=96.3)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=84.6, section_fit=90.3, core=94.1, commodity=92.0
- Briefing cards: 20 / Commodity cards: 14
- Sections: supply:5/5 raw=203, policy:5/5 raw=73, dist:5/5 raw=45, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.70, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.52, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.5, commodity_weak=0.00, commodity_items=6, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=79.0, core=88.0, summary=92.0, missed=80.0, noise=76.0
- Summary: 기본 골격과 개수는 잘 맞췄고, 양파·배추 수급, 농특세·양파 토론회, 과수화상병 등 핵심 축은 대체로 잡혔다. 다만 공급·유통 섹션에 지역 출하식·품평회성 기사와 낮은 적합도의 카드가 섞여 편집 밀도가 떨어졌다. 특히 공급의 성주참외 둔갑 의혹, 토마토 신품종 평가는 섹션 순도에 흠이 있고, 유통은 더 강한 물류·공판장·출하 기사 후보가 있었는데 지역 홍보성 출하 기사들이 일부 우선됐다. 5장 구성은 충족했지만 ‘보이는 후보 대비 최선의 선택’ 기준으로는 90점대 중반까지 주기 어렵다.
- [high] wrong_section: 타 지역 참외 의 '성주 참외 ' 둔갑 정황 포착… 농민들 "박스갈이 의심" [... - 수급보다 원산지·유통 질서 이슈에 가깝고 적합도도 매우 낮다.
- [medium] weak_tail: 충남 대추형 방울 토마토 신품종 경쟁력 입증 - 시장성 평가회 성격으로 당일 수급 이슈성이 약하다.
- [medium] promotional_filler: 대한민국 대표 여름 과일 '고창수박' 본격 출하 …전국 소비자 입맛 공략 - 출하식 중심 지역 홍보 톤이 강하다.
- [medium] weak_section_pick: 애플망고 전국 첫 공선 출하 회, 제주에서 달콤한 ‘첫 수확’ - 첫 출하 기념 성격이 강해 유통 운영 정보가 제한적이다.
- [high] missed_opportunity: 고당도 ‘다올찬수박’ 본격 출하 - raw pool에 더 강한 출하·품질관리 기사였는데 미선정됐다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
