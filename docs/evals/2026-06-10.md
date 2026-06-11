## Daily Eval (2026-06-10)
- Overall: **88.74** (pass)
- Operational: **88.74**
- Scores: completeness=92.8, diversity=96.7, summary=100.0, freshness=100.0, retrieval=87.5, section_fit=100.0, core=93.0, commodity=45.6
- Briefing cards: 18 / Commodity cards: 44
- Sections: supply:5/5 raw=168, policy:4/5 raw=104, dist:4/5 raw=81, pest:5/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.67, summary_presence=1.00, summary_numeric=0.72, fresh_72h=1.00, fit_avg=4.48, false_positive=0.00, weak_core=0.12, editorial_penalty=2.8, commodity_weak=0.00, commodity_strict_link=0.50, commodity_dominant_section=0.58, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: skipped (missing_openai_api_key)

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1), dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=6%, pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
