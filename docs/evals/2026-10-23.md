## Daily Eval (2026-10-23)
- Overall: **90.76** (pass)
- Operational: **92.44**
- Reader quality: **90.76** (clear; penalty=1.7, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=92.0, source=60.0, summary=89.5, freshness=100.0, retrieval=86.0, section_fit=98.6, core=84.9, commodity=90.0
- Briefing cards: 20 / Commodity cards: 47
- Sections: supply:5/5 raw=279, policy:5/5 raw=91, dist:5/5 raw=77, pest:5/5 raw=27
- Metrics: title_unique=1.00, domain_diversity=0.90, low_tier=0.25, summary_presence=1.00, summary_numeric=0.65, fresh_72h=1.00, fit_avg=3.70, false_positive=0.00, hard_reader_issues=0, weak_core=0.25, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=7, commodity_active_today=16, commodity_active_today_unlinked=9, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.71, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (openai_quota_unavailable)
- Model: gpt-5.6-sol

### Improvement Hints
- 최하위 매체 비중이 높습니다. 섹션당 tier-1 1건, 전체 20% 이하를 목표로 하고 같은 이슈의 tier-2+ 원문으로 교체하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
