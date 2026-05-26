## Daily Eval (2026-05-27)
- Overall: **84.91** (warn)
- Operational: **84.91**
- Scores: completeness=92.8, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.0, section_fit=90.7, core=81.2, commodity=95.4
- Briefing cards: 18 / Commodity cards: 33
- Sections: supply:4/5 raw=127, policy:4/5 raw=89, dist:5/5 raw=42, pest:5/5 raw=65
- Metrics: title_unique=1.00, domain_diversity=0.72, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=3.94, false_positive=0.06, weak_core=0.29, editorial_penalty=3.1, commodity_weak=0.00, semantic_penalty=6.7


### Editorial Shadow Eval
- Editorial: **83.00** (target 95, needs_iteration)
- Section count gate: 98.0 (target_met)
- Components: article_selection=79.0, section_fit=75.0, core=74.0, summary=89.0, missed=77.0, noise=72.0
- Summary: 구성은 18건으로 최소 요건은 채웠지만, 공급·정책이 모두 4건에 그친 점이 고점 제한 요인이다. 무엇보다 공급 섹션의 핵심 선택이 소비촉구·품종홍보·기업 솔루션 등 약한 기사로 짜였고, 해충 섹션에는 명백한 오배치 1건이 들어갔다. 유통은 강서시장 분쟁, 수박 출하, 가락상생기금 등 운영성 기사들이 있어 상대적으로 무난했으나, 더 강한 APC 기사와 양파 수출 기사 활용 여지가 있었다. 병해충은 과수화상병 확산을 잡은 점은 좋지만, 가장 중요한 톱픽 자리에 비관련 3D 프린팅 환자식이 들어가 전체 신뢰도를 크게 깎았다.
- [high] wrong_section: [전국 톡톡] "씹고 삼키기 좋게"‥'3D 프린팅'으로 환자식 - 병해충과 무관한 완전한 오배치다.
- [high] weak_core: 우리 몸엔 역시 '신토불이 국산 양파 ' - 수급 기사라기보다 소비 촉구성 홍보에 가깝다.
- [high] promotional: NH농우바이오, 굿초이스 애호박·진하무 6월 추천품종 소개 - 기업 품종 소개성 홍보 기사다.
- [medium] promotional: 사과 장기저장 솔루션 제안, 숨쉬는 저장비닐 '그린라이트' - 제품 제안 중심의 기업 홍보다.
- [high] missed_opportunity: 아직 5월인데 ‘금수박’…이른 더위에 가격 들썩 - 같은 풀에 더 강한 가격 신호 기사가 있었는데 빠졌다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: supply, dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 6%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=6%, pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 6%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
