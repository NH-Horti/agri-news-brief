## Daily Eval (2026-06-19)
- Overall: **84.00** (warn)
- Operational: **91.32**
- Reader quality: **86.61** (capped; penalty=4.7, cap=95.0, reasons=preferred_slot_underfill)
- Quality gate: **84.00** (needs_iteration, editorial_blocking_issue; editorial=84.0, operational=91.3)
- Scores: completeness=89.2, diversity=94.7, summary=100.0, freshness=100.0, retrieval=72.3, section_fit=96.4, core=100.0, commodity=96.1
- Briefing cards: 17 / Commodity cards: 23
- Sections: supply:4/5 raw=190, policy:5/5 raw=178, dist:5/5 raw=48, pest:3/5 raw=11
- Metrics: title_unique=1.00, domain_diversity=0.65, summary_presence=1.00, summary_numeric=0.76, fresh_72h=1.00, fit_avg=4.34, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=7, commodity_active_today=11, commodity_active_today_unlinked=4, commodity_coverage=0.21, commodity_strict_link=0.86, commodity_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 95.5 (soft_fallback)
- Components: article_selection=81.0, section_fit=80.0, core=82.0, summary=93.0, missed=76.0, noise=79.0
- Summary: 전반적으로 읽을 만한 브리핑이지만, 고득점감은 아니다. 정책은 건수는 채웠으나 동일 이슈 중복이 심하고, 공급은 원시 후보가 매우 많은데도 4건에 그쳤으며 핵심 자리에 홍보성 지원 기사가 올라간 점이 크다. 유통은 운영·산지유통 기사와 전자송품장 기사가 있어 기본 축은 맞지만, 지원금 전달·관광기념품 규제 완화 같은 비핵심/오배치가 섞였다. 병해충은 과수화상병 중심 축은 맞았으나 3건 최소치에 머물렀고, 제약사 등록 기사로 채운 선택은 약하다. 요약문 자체는 대체로 명확하다.
- [high] weak_core: “여름채소 생산기반 지키자”…대아청과·농어촌희망재단, 물류기자재... - 지원금 전달식 성격이 강해 공급 섹션 핵심감이 약함.
- [high] missed_opportunity: 외식업 불황에 김치 소비 부진…‘배추 값’ 넉달째 약세 - 원시 후보에 더 직접적인 수급·가격 기사 있었는데 미선정.
- [medium] underfill: 공급 섹션 4건 구성 - raw 후보가 충분한데 선호치 5건 미달.
- [high] duplication: LNG·LPG 할당관세 0% 관련 3건 - 사실상 동일 정책을 3장으로 반복해 지면 효율이 낮음.
- [high] wrong_section: 오창농협, 청원생명 ‘꺼리’ 햇 감자 출하 - 정책보다 출하·판로 성격이 강함.

### Improvement Hints
- 선정 결과가 약한 섹션이 있습니다: pest. 해당 섹션은 raw 후보가 충분하므로 임계치/재배치 규칙을 다시 보는 편이 좋습니다.
- 리콜 시드 결손이 보입니다: supply, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: supply(-1), pest(-2). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
