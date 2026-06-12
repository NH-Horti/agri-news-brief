## Daily Eval (2026-06-12)
- Overall: **84.00** (warn)
- Operational: **97.82**
- Reader quality: **97.64** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **84.00** (needs_iteration, editorial_below_target; editorial=84.0, operational=97.8)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.2, section_fit=97.2, core=92.0, commodity=100.0
- Briefing cards: 20 / Commodity cards: 14
- Sections: supply:5/5 raw=204, policy:5/5 raw=74, dist:5/5 raw=44, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.80, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=3.69, false_positive=0.00, hard_reader_issues=0, weak_core=0.17, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=7, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=85.0, core=86.0, summary=92.0, missed=78.0, noise=80.0
- Summary: 전반적으로 5개 섹션 수는 맞췄고 핵심 이슈인 양파 가격난·여름배추 수급·과수화상병은 잡았다. 다만 정책 섹션의 중복 논점, 공급 섹션의 약한 꼬리 기사, 유통 섹션의 판촉·설명회성 기사 비중이 아쉽다. 원시 후보군에 더 강한 유통/산지거래 기사들이 보였는데 일부 자리를 덜 중요한 운영·홍보성 기사로 채워 점수를 깎는다.
- [high] duplication: 농민의길 “농특세, 농산물 가격 안정 에 우선 써야” / 농어촌기본소득 재원 농특세 활용 농민단체 반대 목소리 - 같은 성명 논점을 사실상 중복 선정했다.
- [medium] wrong_priority: 창녕서 마늘 전 과정 기계화 기술 공개…농촌 인력난 해법 제시 - 성과공유회 성격이 강해 수급 핵심도는 낮다.
- [medium] wrong_priority: 경북 영천시, 마늘 수확 작업 기계화 및 농가 경영 효율화에 주력 - 지자체 장비보급 안내성 기사로 전국 수급 임팩트가 약하다.
- [medium] section_fit: “ 농산물 판매, 디지털 전환해야”…전남농협, 농협몰 설명회 열어 - 실제 유통 운영보다 설명회·참여 안내 비중이 크다.
- [medium] noise: 고당도 ‘다올찬수박’ 본격 출하 - 출하 기사지만 판촉성 톤이 강하다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
