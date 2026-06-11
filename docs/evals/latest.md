## Daily Eval (2026-06-12)
- Overall: **82.00** (warn)
- Operational: **95.00**
- Quality gate: **82.00** (needs_iteration, editorial_below_target; editorial=82.0, operational=95.0)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.2, section_fit=96.9, core=88.4, commodity=92.0
- Briefing cards: 19 / Commodity cards: 18
- Sections: supply:5/5 raw=206, policy:5/5 raw=84, dist:4/5 raw=46, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.74, summary_presence=1.00, summary_numeric=0.79, fresh_72h=1.00, fit_avg=3.86, false_positive=0.00, weak_core=0.17, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=9, commodity_coverage=0.27, commodity_strict_link=0.89, commodity_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=80.0, section_fit=72.0, core=74.0, summary=90.0, missed=79.0, noise=71.0
- Summary: 전반적으로 당일 농정·수급 이슈를 다수 포착했고 요약도 실용적이다. 다만 편집 품질 기준으로 보면 공급·정책·병해충에서 중복·오분류·약한 꼬리 카드가 섞였고, 유통은 원시 후보가 충분한데도 4건에 그쳐 목표 미달이다. 특히 정책의 동일 성명 중복, 병해충의 화상병 사진/현장점검 중복, 공급의 생활정보성 카드와 사건사고성 코어는 감점 요인이다.
- [high] wrong_section: 사라진 하우스 개폐기…한라봉 농사 망쳐 - 수급 이슈보다 사건사고 성격이 강한데 코어로 배치됨.
- [medium] weak_tail: 감자만 따로 보관하면 손해… 사과 와 함께 두니 저장 기간 길어진 이유 - 생활정보성 기사로 농업 데일리 핵심 흐름과 거리가 멂.
- [high] duplicate: 농민의길 “농특세, 농산물 가격 안정에 우선 써야” / "농어촌특별세, 농산물 가격안정에 사용해야" - 동일 성명 기사 중복으로 슬롯 낭비.
- [medium] filler: 송미령 장관, '특별성과 포상' 수여식 실시 - 농정 독자 관점에서 실질 정책 가치가 낮은 내부행사성 기사.
- [medium] filler: 안동형일자리사업 창업기업지원사업 성과, 글로벌 진출로 확산 - 지역 사업 홍보성 성격이 강해 전국 농정 섹션과 거리감이 큼.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
