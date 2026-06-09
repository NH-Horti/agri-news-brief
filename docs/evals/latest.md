## Daily Eval (2026-06-10)
- Overall: **88.00** (pass)
- Operational: **91.95**
- Quality gate: **88.00** (needs_iteration, editorial_below_target; editorial=88.0, operational=92.0)
- Scores: completeness=92.8, diversity=100.0, summary=100.0, freshness=100.0, retrieval=87.5, section_fit=100.0, core=92.4, commodity=98.5
- Briefing cards: 18 / Commodity cards: 39
- Sections: supply:5/5 raw=168, policy:4/5 raw=104, dist:4/5 raw=81, pest:5/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.72, summary_presence=1.00, summary_numeric=0.83, fresh_72h=1.00, fit_avg=4.46, false_positive=0.00, weak_core=0.12, editorial_penalty=2.8, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **88.00** (target 95, needs_iteration)
- Section count gate: 96.0 (soft_fallback)
- Components: article_selection=86.0, section_fit=89.0, core=87.0, summary=92.0, missed=84.0, noise=88.0
- Summary: 전반적으로 핵심 이슈는 잡았지만, 고득점감은 아니다. 공급·병해충은 비교적 탄탄하나, 정책·유통에서 5장 목표를 채우지 못했고 남은 자리도 더 나은 후보 대신 행사성·로컬성 기사로 메운 흔적이 있다. 특히 유통 섹션은 운영·물류·시장 기능 기사보다 지역 출하/개장 기사 비중이 높아 섹션 정체성이 약해졌다. 병해충은 화상병 축을 잘 잡았지만 충북 화상병 중복도가 높다. 요약은 대체로 유용하다.
- [medium] underfill: 정책 섹션 4건만 구성 - 원시 후보가 충분한데 5건 목표 미달.
- [medium] underfill: 유통 섹션 4건만 구성 - 후보 풀이 충분한데 soft fallback 사용.
- [high] wrong_emphasis: 음성 농협들, 다올찬 수박 줄줄이 출하…가파른 성장세 - 출하 개시·브랜드 성장 소개 중심으로 유통 운영성은 약함.
- [medium] promotional_filler: '산내 델라웨어' 첫 대만행…대전 포도 해외 식탁 오른다 - 320kg 지역 수출 홍보성 소식으로 공급 핵심성과 약함.
- [medium] weak_tail: 마늘 수확 기계화·'무멀칭 재배' 기술 고도화 나선다 - 기술 시범사업은 당일 수급 브리프의 우선순위가 낮음.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: policy(-1), dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=6%, pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
