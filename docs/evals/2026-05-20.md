## Daily Eval (2026-05-20)
- Overall: **94.11** (pass)
- Operational: **94.11**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=99.9, core=100.0, commodity=100.0
- Briefing cards: 16 / Commodity cards: 41
- Sections: supply:5/3 raw=143, policy:4/3 raw=87, dist:3/3 raw=53, pest:4/3 raw=57
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.25, false_positive=0.00, weak_core=0.00, editorial_penalty=4.8, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Components: article_selection=80.0, section_fit=76.0, core=74.0, summary=89.0, missed=83.0, noise=72.0
- Summary: 핵심 이슈인 봄채소 약세와 과수화상병은 잘 잡았지만, 공급·유통 섹션에 지역 홍보성/행사성 카드가 섞였고 유통 핵심축이 약하다. 정책 섹션도 제도 변화보다 수급 대응 기사 비중이 높아 편집 의도가 다소 흐려졌다. 전반적으로 읽을 만하지만 95점급 편집으로 보긴 어렵다.
- [high] wrong_section: NH농협 창녕군지부, 마늘 망 지원… 농업인 영농비 절감 기대 - 지역 지원행사성 기사로 수급 이슈성이 약함.
- [high] weak_core: NH농협 창녕군지부, 마늘 망 지원… 농업인 영농비 절감 기대 - 코어로 둘 수준의 파급력과 데이터가 부족함.
- [high] promotional_filler: 청주 오송농협, ‘청원생명 맛찬동이’ 수박 본격 출하 - 브랜드 출하 홍보에 가까워 유통 구조 변화 정보가 약함.
- [medium] weak_core: 청주 오송농협, ‘청원생명 맛찬동이’ 수박 본격 출하 - 유통 섹션 코어치고 운영·제도·채널 변화가 빈약함.
- [medium] duplicate_theme: “예측보다 빨랐다”…‘과수화상병’ 충주·원주서 잇따라 발생 / ‘ 과수화상병 ’ 주의보 - 동일 화상병 이슈를 비슷한 각도로 중복 배치.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=6%, promotional_filler=12%, dist_weak_ops=6%, pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
