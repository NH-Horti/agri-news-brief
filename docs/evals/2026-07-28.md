## Daily Eval (2026-07-28)
- Overall: **81.06** (warn)
- Operational: **92.11**
- Reader quality: **83.65** (clear; penalty=8.5, cap=100.0, reasons=clear)
- Quality gate: **81.06** (needs_iteration, editorial_major_issue; editorial=82.7, operational=92.1)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=100.0, retrieval=88.8, section_fit=100.0, core=68.6, commodity=98.1
- Briefing cards: 20 / Commodity cards: 41
- Sections: supply:5/5 raw=179, policy:5/5 raw=111, dist:5/5 raw=65, pest:5/5 raw=53
- Metrics: title_unique=1.00, domain_diversity=0.85, low_tier=0.15, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=3.50, false_positive=0.00, hard_reader_issues=0, weak_core=0.22, editorial_penalty=4.7, commodity_weak=0.00, commodity_items=12, commodity_active_today=16, commodity_active_today_unlinked=4, commodity_coverage=0.36, commodity_strict_link=0.83, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.65** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 82.70; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=91.0, core=74.0, summary=87.0, missed=79.0, noise=83.0
- Summary: 모든 섹션을 5건씩 채웠고 최신성·섹션 적합성·요약 가독성은 양호하다. 다만 정책에서 지역 안전점검을 핵심으로 두고 최고 적합도의 구조개혁 인터뷰를 비핵심으로 처리했으며, 유통의 6000억원 사업 평가와 병해충의 과수화상병 확산 기사도 핵심에서 빠졌다. 정책·유통 원자료에 더 강한 전국 단위 정책과 구체적 판로 사업이 있었는데 일부 전망성·현장점검 카드가 이를 대신해 일일 브리핑의 우선순위가 약해졌다.
- [major] weak_core: [아주초대석] 홍문표 aT사장 "농산물 수급 불안, 韓 농업의 취약한 구조... - 정책 섹션 최고 적합도이며 수급 구조와 기후 대응을 다루지만 비핵심으로 밀렸다.
- [moderate] weak_core: 강원농업기술원, 폭염 대응 농업인 안전 현장지원 강화 - 지역 농가 방문·점검 중심이라 전국 수급정책 기사보다 핵심성이 낮다.
- [moderate] weak_core: [AI로 읽는 경제] 농산물 유통개혁 6000억 투입했지만…"성과 검증·농협... - 6000억원 유통개혁 사업의 성과 검증과 농협 역할을 다룬 대표 유통 현안이다.
- [moderate] weak_core: 과수화상병 '미리바 스프레이'로 진단 가능 - 전국 122농가·51.9㏊ 발생과 사과 농가 급증을 담아 일반 방제 당부보다 핵심성이 높다.
- [moderate] missed_candidate: 농식품부, '모두의 상생' 출범…농업·기업 함께 키운다 - 생산부터 판로·수출까지 연결하는 전국 단위 사업으로 지역 APC 점검보다 파급력이 크다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=15%, dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
