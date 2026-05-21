## Daily Eval (2026-05-21)
- Overall: **93.40** (pass)
- Operational: **93.40**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=88.8, section_fit=92.2, core=100.0, commodity=94.0
- Briefing cards: 15 / Commodity cards: 60
- Sections: supply:4/3 raw=155, policy:3/3 raw=101, dist:4/3 raw=38, pest:4/3 raw=72
- Metrics: title_unique=1.00, domain_diversity=0.87, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.50, false_positive=0.00, weak_core=0.00, editorial_penalty=4.5, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Components: article_selection=82.0, section_fit=79.0, core=85.0, summary=90.0, missed=80.0, noise=78.0
- Summary: 핵심 이슈인 양파 공급과잉·과수화상병은 잘 잡았지만, 섹션 배치와 후순위 카드의 편집력이 아쉽다. 특히 policy에 현장 수급 기사(무안 양파)를 넣고, supply·dist에 지자체 신청/견학/간담회성 기사들이 섞이면서 섹션 정체성이 흐려졌다. raw pool상 더 강한 대체 후보가 일부 보였고, 홍보성 마늘 기사와 지역 행정성 기사 비중도 감점 요소다.
- [high] wrong_section: 무안 양파 값 폭락…"캘수록 손해, 갈아엎어도 소용없다" - 정책 발표보다 산지 가격 급락 현장 기사 성격이 강함.
- [high] promotional_core: 마늘의무자조금관리위원회, "마늘가격 지킬 수 있어요" - 이해관계 단체 입장문 중심의 홍보성 기사다.
- [high] filler: 무주군, 사과 ·포도 등 60억 규모 농산물 가격안정 지원…29일까지 신청 - 지역 사업 신청 공고성 기사로 전국 브리핑 가치가 낮다.
- [medium] wrong_section: 충남도농기원, 시설채소 현장기술지원단 가동..."폭염 속 토마토 ·오이... - 공급 동향보다 재배기술·현장지원 기사에 가깝다.
- [medium] filler: 강원 농협 , 선진 산지유통 현장 벤치마킹…농산물 경쟁력 강화 모색 - 견학·벤치마킹 행사성 기사로 실질 유통 변화가 약하다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=20%, pest_theme_duplicate=13%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
