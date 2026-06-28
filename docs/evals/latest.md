## Daily Eval (2026-06-23)
- Overall: **95.69** (pass)
- Operational: **97.17**
- Reader quality: **96.99** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **95.69** (needs_iteration, editorial_below_target_bounded_penalty; editorial=82.0, operational=97.2)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.6, section_fit=97.2, core=85.4, commodity=95.6
- Briefing cards: 20 / Commodity cards: 50
- Sections: supply:5/5 raw=200, policy:5/5 raw=117, dist:5/5 raw=52, pest:5/5 raw=35
- Metrics: title_unique=1.00, domain_diversity=1.00, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=3.34, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=12, commodity_active_today=17, commodity_active_today_unlinked=5, commodity_coverage=0.36, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.58, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=78.0, core=84.0, summary=89.0, missed=79.0, noise=74.0
- Summary: 핵심 이슈인 양파 공급과잉과 과수화상병, 도매시장 해킹은 잘 잡았지만, 섹션 간 중복·오배치와 약한 꼬리 기사 비중이 점수를 깎았다. 특히 supply·policy에서 같은 전북 양파 대책이 반복됐고, dist는 자두 공판장 개장·해외 사례·직거래 기획 등 운영 현장성보다 약한 선택이 섞였다. 5장 수는 채웠지만 후보풀이 충분한 날의 95점대 편집 완성도에는 못 미친다.
- [high] duplication: 전북, 양파 수급 안정 대책 추진...농가 경영안정 지원 - supply와 사실상 같은 전북 양파 대책 반복.
- [medium] duplication: 양파 풍년에 값 하락 우려 ‘쑥’…전북도, 수급 안정 대책 ‘신발끈’ - 같은 전북 양파 기사 3중 편성으로 새 정보 부족.
- [medium] wrong_section: 전북도, 양파 가격 하락 대응 수급 안정 대책 추진 - 산지 수급 대응이지만 정책 섹션과 더 맞고 중복도 유발.
- [medium] weak_tail: “기후변화 대응” 농산물 생산· 수급 안정 에 힘 합친다 - MOU성 기사로 즉시성·시장 파급이 약함.
- [medium] duplication: aT-농과원, CA 기술 공조… 여름 배추 수급 잡는다 - 윗기사와 사실상 같은 협약/협력 내용 반복.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
