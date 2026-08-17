## Daily Eval (2026-08-18)
- Overall: **87.22** (pass)
- Operational: **87.58**
- Reader quality: **87.22** (clear; penalty=0.4, cap=100.0, reasons=clear)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=88.0, freshness=40.0, retrieval=92.5, section_fit=100.0, core=100.0, commodity=88.4
- Briefing cards: 20 / Commodity cards: 50
- Sections: supply:5/5 raw=414, policy:5/5 raw=130, dist:5/5 raw=78, pest:5/5 raw=62
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.20, summary_presence=1.00, summary_numeric=0.85, fresh_72h=0.50, fit_avg=3.69, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.2, commodity_weak=0.00, commodity_items=12, commodity_active_today=24, commodity_active_today_unlinked=12, commodity_coverage=0.36, commodity_strict_link=0.92, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.75, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (forced_sla_recovery)
- Model: gpt-5.6-sol

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 최신성 점수가 내려갔습니다. 동일 이벤트 중 최신 기사 우선, 96시간 초과 기사 감점을 더 강하게 주는 편이 안정적입니다.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
- 오래된 기사일수록 배경 설명은 줄이고 이번 보고일 기준으로 새롭게 확인된 조치나 수급 신호를 먼저 적는다.
