## Daily Eval (2026-06-12)
- Overall: **84.00** (warn)
- Operational: **97.42**
- Reader quality: **90.00** (capped; penalty=4.9, cap=90.0, reasons=pest_theme_duplicate)
- Quality gate: **84.00** (needs_iteration, editorial_below_target; editorial=84.0, operational=97.4)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.2, section_fit=97.2, core=91.9, commodity=100.0
- Briefing cards: 20 / Commodity cards: 14
- Sections: supply:5/5 raw=206, policy:5/5 raw=75, dist:5/5 raw=44, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.95, fresh_72h=1.00, fit_avg=3.69, false_positive=0.00, hard_reader_issues=0, weak_core=0.17, editorial_penalty=0.5, commodity_weak=0.00, commodity_items=7, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.43, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=83.0, section_fit=82.0, core=87.0, summary=92.0, missed=79.0, noise=80.0
- Summary: 전체적으로는 4개 섹션을 5건씩 채우고 핵심 이슈인 양파 수익성 악화와 과수화상병 확산을 잡아낸 점은 좋다. 다만 정책·유통·병해충에서 약한 꼬리 기사와 중복성 높은 선택이 섞였고, raw pool에 보이는 더 적합한 대안 일부를 놓쳤다. 특히 정책은 성명·지원사업·농협자금성 기사 비중이 높아 무게감이 약했고, 병해충은 화상병 3건에 일반 재해성 기사 2건이 붙어 섹션 선명도가 떨어진다. 유통도 물류·공판장·저온유통은 맞지만 수박 출하식 2건은 홍보성 색채가 강하다.
- [high] wrong_section: 함평군, 장마철 농작물 피해 예방 강화 - 병해충보다 일반 재해예방 기사다.
- [high] wrong_section: 여름철 태풍·집중호우 '선제적 차단' - 해충·병해보다 재난대응 일반 기사다.
- [medium] duplicate_theme: 과수화상병 예찰 현장 점검하는 이승돈 농진청장 - 1번 화상병 점검 기사와 사실상 중복이다.
- [medium] promotional_filler: 고당도 ‘다올찬수박’ 본격 출하 - 출하·판촉 중심 지역 홍보성이 강하다.
- [medium] promotional_filler: 대한민국 대표 여름 과일 '고창수박' 본격 출하 …전국 소비자 입맛 공략 - 출하식 중심 홍보 기사다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
