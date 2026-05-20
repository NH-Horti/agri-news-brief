## Daily Eval (2026-05-20)
- Overall: **94.25** (pass)
- Operational: **94.25**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=99.9, core=100.0, commodity=100.0
- Briefing cards: 16 / Commodity cards: 43
- Sections: supply:5/3 raw=145, policy:4/3 raw=88, dist:3/3 raw=53, pest:4/3 raw=58
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.25, false_positive=0.00, weak_core=0.00, editorial_penalty=4.7, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Components: article_selection=78.0, section_fit=76.0, core=80.0, summary=88.0, missed=79.0, noise=72.0
- Summary: 핵심 이슈인 양배추 급락과 과수화상병은 잘 잡았지만, 공급·유통 섹션에 지역 농협 행사성 기사와 출하 개시성 홍보물이 섞여 편집 완성도가 떨어진다. 정책 섹션도 정부 수입·관세 대책과 양파 수출 기사 조합은 무난하나, 더 구조적인 정책 이슈 대비 임팩트가 약하다. 전반적으로 읽을 만하지만 95점대 편집으로 보기엔 노이즈와 섹션 경계 관리가 아쉽다.
- [high] promotional_filler: NH농협 창녕군지부, 마늘 망 지원… 농업인 영농비 절감 기대 - 지역성 강한 지원 행사로 수급 뉴스 가치 낮음.
- [high] wrong_section: 청주 오송농협, ‘청원생명 맛찬동이’ 수박 본격 출하 - 유통 구조보다 지역 출하 홍보에 가까움.
- [medium] promotional_filler: 강원 농협 연합판매사업 협의회, 2026 산지 유통 현장투어 개최 - 벤치마킹 행사 기사로 실질 유통 변화 정보 부족.
- [medium] theme_duplication: ‘ 과수화상병 ’ 주의보 - 1번 화상병 발생 기사와 정보 중복, 신문 내 B컷 성격 강함.
- [high] weak_core: NH농협 창녕군지부, 마늘 망 지원… 농업인 영농비 절감 기대 - 코어로 둘 만한 전국성·시장성 부족.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (policy_wrong_section=6%, promotional_filler=12%, dist_weak_ops=6%, pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
