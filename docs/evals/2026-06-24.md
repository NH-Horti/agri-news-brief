## Daily Eval (2026-06-24)
- Overall: **97.48** (pass)
- Operational: **98.38**
- Reader quality: **98.38** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **97.48** (needs_iteration, editorial_below_target_bounded_penalty; editorial=86.0, operational=98.4)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=94.2, commodity=96.8
- Briefing cards: 20 / Commodity cards: 25
- Sections: supply:5/5 raw=216, policy:5/5 raw=103, dist:5/5 raw=64, pest:5/5 raw=36
- Metrics: title_unique=1.00, domain_diversity=0.70, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=3.89, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=9, commodity_active_today=12, commodity_active_today_unlinked=3, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.56, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=85.0, section_fit=83.0, core=84.0, summary=92.0, missed=81.0, noise=82.0
- Summary: 전반적으로 5장씩 채워 기본 구성은 좋고, 수급·병해충의 주요 이슈도 대체로 포착했다. 다만 공급 섹션의 중복성, 정책/유통 섹션의 홈플러스 미수금 중복 배치, 유통 섹션의 약한 기념·홍보성 기사 채택, 그리고 더 강한 원시 후보를 두고 덜 적합한 기사를 고른 점이 보여 90점대 중반까지는 어렵다.
- [high] duplication: 전북도, 양파 가격 하락 대응 수급 안정 대책 추진 / “양파 ‘풍년의 눈물’ 막자”… 전북, 4500t 출하 정지 - 같은 사안을 두 장으로 반복했다.
- [high] duplication: 홈플러스 미수금에 산지유통 조직 '비상'…정부, 300억 긴급 금융지원 / 홈플러스 납품대금 미수 산지유통 에 정부 금융지원 - 동일 정책 사안 중복이다.
- [medium] wrong_section: 홈플러스 미수금에 산지 돈줄 막혀…정부 300억원 긴급 지원 - 유통 이슈이긴 하나 정책 섹션과 주제가 사실상 겹친다.
- [medium] weak_core: 가락 시장 41년, 'AX 도매시장 ' 정조준 - 기념식 성격이 강해 당일 운영 충격·거래 변화 기사보다 약하다.
- [medium] promotional_filler: 창원 동읍농협, 단감농가에 탄저병 약제 지원 - 병해충 현황보다 기관 지원 행사 성격이 강하다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
