## Daily Eval (2026-07-08)
- Overall: **89.74** (pass)
- Operational: **97.26**
- Reader quality: **97.08** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **89.74** (needs_major_iteration, editorial_major_issue; editorial=78.7, operational=97.3)
- Scores: completeness=100.0, diversity=96.4, source=100.0, summary=98.5, freshness=100.0, retrieval=89.4, section_fit=100.0, core=89.3, commodity=96.8
- Briefing cards: 20 / Commodity cards: 17
- Sections: supply:5/5 raw=195, policy:5/5 raw=143, dist:5/5 raw=90, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.65, low_tier=0.15, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=4.45, false_positive=0.00, hard_reader_issues=0, weak_core=0.14, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=9, commodity_active_today=11, commodity_active_today_unlinked=2, commodity_coverage=0.27, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.56, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **78.65** (daily target 88, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 81.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=4, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=83.0, core=77.0, summary=78.0, missed=74.0, noise=80.0
- Summary: 카드 수와 신선도는 충족했지만, 편집 품질은 목표치에 못 미친다. 배추 약세, 가격안정제, 과수화상병, APC 자동화 등 핵심 소재는 잡았으나 정책 중복, 유통 섹션의 약한 지역·교육성 카드, 공급 섹션의 더 강한 산지 르포 누락이 크다. 특히 제주 농산물 항공운송 차질 같은 뚜렷한 물류 이슈를 빠뜨리고 동화청과 교육·구지농협 계약재배를 유통 핵심처럼 배치한 점이 아쉽다.
- [major] duplicate_story: 농경연 "물가 정책, 취약계층 중심 맞춤형 정책으로 발전해야" - 1번 정책 카드의 뉴시스 KREI 취약계층 물가정책 기사와 사실상 같은 연구·메시지다.
- [major] missed_candidate: 제주 농산물 항공운송 ‘이중고’… 운임 치솟고 적재공간 줄어 농가 한숨 - 운임 상승과 적재공간 축소라는 구체적 물류 차질 기사로, 유통 섹션 최우선 후보인데 누락됐다.
- [major] weak_core: 대구 달성 구지농협, 계약재배로 농가 소득 견인 - 지역 농협 계약재배 미담에 가까워 유통 핵심 카드로는 약하다.
- [moderate] promotional_filler: "출하 전략으로 제값 받는다"…동화청과, 도매시장 유통 노하우 전수 - 교육·견학 프로그램 소개에 가까워 전국 독자에게 줄 유통 정보 가치가 낮다.
- [major] missed_candidate: [주산지 르포] 얼갈이배추·오이 경락값 5년만에 최저…“안전장치 시급...” - 가격 폭락 현장성과 품목별 수급 신호가 강한데, 약한 행정성·의견성 카드가 대신 들어갔다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
