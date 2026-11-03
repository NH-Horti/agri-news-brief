## Daily Eval (2026-11-04)
- Overall: **86.19** (pass)
- Operational: **91.95**
- Reader quality: **86.19** (clear; penalty=5.8, cap=100.0, reasons=clear)
- Scores: completeness=93.0, diversity=96.0, source=80.0, summary=97.0, freshness=100.0, retrieval=82.4, section_fit=97.2, core=100.0, commodity=90.0
- Briefing cards: 20 / Commodity cards: 47
- Sections: supply:5/5 raw=434, policy:5/5 raw=238, dist:5/5 raw=101, pest:5/5 raw=20
- Metrics: title_unique=1.00, domain_diversity=0.80, low_tier=0.20, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.37, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=3.2, commodity_weak=0.00, commodity_items=7, commodity_active_today=14, commodity_active_today_unlinked=7, commodity_coverage=0.21, commodity_strict_link=0.86, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.71, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
