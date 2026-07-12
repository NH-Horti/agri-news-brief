## Daily Eval (2026-07-06)
- Overall: **93.05** (pass)
- Operational: **95.86**
- Reader quality: **95.14** (clear; penalty=0.7, cap=100.0, reasons=clear)
- Quality gate: **93.05** (needs_iteration, editorial_major_issue; editorial=84.7, operational=95.9)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=90.0, retrieval=89.4, section_fit=87.7, core=100.0, commodity=99.8
- Briefing cards: 20 / Commodity cards: 29
- Sections: supply:5/5 raw=255, policy:5/5 raw=138, dist:5/5 raw=100, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.70, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=4.26, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.4, commodity_weak=0.00, commodity_items=11, commodity_active_today=16, commodity_active_today_unlinked=5, commodity_coverage=0.33, commodity_strict_link=0.91, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.36, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.65** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 86.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=86.0, section_fit=87.0, core=90.0, summary=78.0, missed=80.0, noise=84.0
- Summary: 전 섹션 5건을 채웠고 핵심 수급·정책·화상병 이슈는 대체로 잡았다. 다만 공급 섹션은 KREI 7월 관측 기사에 과도하게 몰렸고, 유통 섹션은 더 강한 산지유통·공판장 후보를 두고 홍보성·지역행사성 카드가 일부 들어갔다. 병해충은 충북 과수화상병 카드가 중복 테마로 겹치며 순천 4차 방제 같은 대체 후보를 놓쳤다. 여러 요약이 원문 스니펫처럼 잘리거나 HTML/따옴표가 섞여 독자용 완성도가 떨어진다.
- [moderate] duplicate_theme: 여름배추·무 재배면적 감소…배추·참외·수박 가격 은 하락 / 7월 과채 출하량 늘고 가격 은 하락 전망 / 배값 강세 이어진다… - 공급 5건 중 3건이 KREI 7월 관측 전망으로 구성돼 관측 리포트 테마가 과밀하다.
- [moderate] missed_candidate: “오이 한 상자 5200원”…과채류 가격 폭락에 농가 비상 - 신선한 현장 가격 급락 기사인데 마늘 경매·점검성 카드보다 공급 독자 가치가 높다.
- [moderate] promotional_filler: aT, ' 농산물 꾸러미' 키우고... K-푸드 수출 해법 넓힌다 - 요약이 기관 발언 중심이고 구체적 물류·도매시장·판매 운영 정보가 약하다.
- [moderate] missed_candidate: 경북지역 조합공동사업법인, 농산물 판매확대로 농가소득 증대 앞장 - 산지유통 경쟁력·APC·조공법인 운영 논의가 있어 dist 섹션 적합도가 선택된 약한 tail보다 높다.
- [moderate] duplicate_theme: 폭염에 주춤한 충북 과수화상병… / 과수화상병 조기 신고가 피해 줄인다 - 둘 다 충북 과수화상병 소강·예찰 메시지라 핵심 카드 2개가 같은 지역·같은 대응 국면에 묶인다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (dist_weak_ops=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
