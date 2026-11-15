## Daily Eval (2026-11-16)
- Overall: **73.85** (warn)
- Operational: **84.47**
- Reader quality: **73.85** (capped; penalty=10.6, cap=90.0, reasons=pest_theme_duplicate)
- Scores: completeness=100.0, diversity=96.0, source=80.0, summary=91.0, freshness=94.3, retrieval=91.9, section_fit=75.0, core=77.6, commodity=90.9
- Briefing cards: 20 / Commodity cards: 67
- Sections: supply:5/5 raw=477, policy:5/5 raw=140, dist:5/5 raw=74, pest:5/5 raw=55
- Metrics: title_unique=1.00, domain_diversity=0.90, low_tier=0.20, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.23, false_positive=0.05, hard_reader_issues=0, weak_core=0.29, editorial_penalty=0.9, commodity_weak=0.00, commodity_items=13, commodity_active_today=17, commodity_active_today_unlinked=4, commodity_coverage=0.39, commodity_strict_link=0.92, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.69, semantic_penalty=6.0


### Editorial Shadow Eval
- Editorial: skipped (guaranteed_delivery_final)
- Model: gpt-5.6-sol

### Improvement Hints
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 5%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, dist_weak_ops=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 15%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
