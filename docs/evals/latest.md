## Daily Eval (2026-11-26)
- Overall: **89.20** (pass)
- Operational: **93.61**
- Reader quality: **89.20** (clear; penalty=4.4, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=88.0, freshness=100.0, retrieval=91.2, section_fit=100.0, core=100.0, commodity=88.0
- Briefing cards: 20 / Commodity cards: 60
- Sections: supply:5/5 raw=400, policy:5/5 raw=93, dist:5/5 raw=119, pest:5/5 raw=60
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.20, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=4.14, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.5, commodity_weak=0.00, commodity_items=10, commodity_active_today=16, commodity_active_today_unlinked=6, commodity_coverage=0.30, commodity_strict_link=0.90, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.90, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
