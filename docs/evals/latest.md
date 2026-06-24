## Daily Eval (2026-06-25)
- Overall: **81.00** (warn)
- Operational: **96.43**
- Reader quality: **86.00** (capped; penalty=3.7, cap=86.0, reasons=commodity_pool_false_link, commodity_pool_false_link_severe, preferred_slot_underfill)
- Quality gate: **81.00** (needs_major_iteration, editorial_blocking_issue; editorial=81.0, operational=96.4)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=100.0, retrieval=84.2, section_fit=97.5, core=98.3, commodity=98.8
- Briefing cards: 19 / Commodity cards: 32
- Sections: supply:5/5 raw=163, policy:5/5 raw=100, dist:4/5 raw=27, pest:5/5 raw=30
- Metrics: title_unique=1.00, domain_diversity=0.84, summary_presence=1.00, summary_numeric=0.89, fresh_72h=1.00, fit_avg=4.10, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=9, commodity_active_today=12, commodity_active_today_unlinked=3, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.18, commodity_dominant_section=0.44, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **81.00** (target 95, needs_major_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=79.0, section_fit=76.0, core=80.0, summary=89.0, missed=77.0, noise=73.0
- Summary: 전반적으로 상반기 농산물 가격 폭락·가격안정제 논점을 잘 잡았지만, 섹션별 기사 배치와 말단 카드 품질이 약하다. 특히 supply에 축제·급식 현장 기사가 섞여 노이즈가 컸고, pest는 동일 포항 협업방제 기사가 중복됐다. dist도 4장 soft fallback에 머물렀는데, 원시 후보상 5장을 채울 여지가 있었고 핵심 카드 역시 기부성 지원 기사라 약하다. 좋은 핵심 이슈는 있으나 편집 완성도는 목표 95에 한참 못 미친다.
- [high] wrong_section: 광주시 '제24회 퇴촌 토마토 거리축제' 33만여명 방문 속 마무리 - 지역 축제 마감 기사로 수급 핵심성이 낮다.
- [high] wrong_section: 새벽 7시 30분 급식실 검수대 앞, 15년 차 영양사의 토로 - 학교 급식 노동 기사로 공급 섹션과 거리가 멀다.
- [high] weak_core: “물류·영농기자재 확충하세요”…중앙청과, 광주광역시 서창농협에 2... - 기부 전달 기사라 유통 운영 핵심 기사로는 약하다.
- [medium] underfill: dist 섹션 4장 편성 - raw 후보가 27건인데 5장 대신 soft fallback 사용.
- [high] duplicate: 포항시 돌발해충 협업 방제 2건 중복 선정 - 동일 현안·동일 내용의 매체만 다른 중복이다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
