## Daily Eval (2026-06-04)
- Overall: **83.00** (warn)
- Operational: **87.46**
- Quality gate: **83.00** (needs_iteration, editorial_below_target; editorial=83.0, operational=87.5)
- Scores: completeness=96.4, diversity=100.0, summary=100.0, freshness=100.0, retrieval=88.8, section_fit=83.2, core=85.3, commodity=99.2
- Briefing cards: 19 / Commodity cards: 37
- Sections: supply:5/5 raw=211, policy:5/5 raw=184, dist:4/5 raw=67, pest:5/5 raw=102
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.68, fresh_72h=1.00, fit_avg=4.66, false_positive=0.05, weak_core=0.14, editorial_penalty=0.4, commodity_weak=0.00, semantic_penalty=6.3


### Editorial Shadow Eval
- Editorial: **83.00** (target 95, needs_iteration)
- Section count gate: 98.0 (soft_fallback)
- Components: article_selection=81.0, section_fit=77.0, core=80.0, summary=90.0, missed=79.0, noise=76.0
- Summary: 전반적으로 주요 이슈는 일부 잘 잡았지만, 공급·정책·유통에서 약한 선택과 중복성이 점수를 깎았다. 공급은 양파 급락 코어는 적절하나 지역성 포도 주의보와 인물성 배 기사, 양파 중복성으로 밀도가 떨어졌다. 정책은 농협 홍보성 기사와 물가 기사 중복이 크다. 유통은 4건에 그쳤고, 실제 유통·경매·공판장·선박수출 후보가 더 있었는데 운영성보다 현장점검·인물성 기사 비중이 높았다. 병해충은 화상병 중심축은 맞지만 제품홍보성 꼬리가 명확한 감점 요소다.
- [high] wrong_section_or_weak_fit: 옥천군농업기술센터, 폭염 속 포도 생리장해 주의 당부 - 전국 수급보다 지역 재배관리 공지에 가깝다.
- [high] promotional_or_feature_filler: 배 한 알에 담긴 농민의 책임감 - 인물 미담형 기사로 수급 정보성이 약하다.
- [medium] duplication: 양파 값 폭락에 농가 울상..생산비도 못 건져 - 1번 양파 급락 기사와 주제가 과도하게 겹친다.
- [high] weak_core: 인력난 해소·스마트팜 확산…농협 강호동 "정부의 든든한 농정 파트너... - 실질 정책보다 농협 활동 소개 성격이 강하다.
- [high] duplication: [종합] 중동發 고유가 직격탄…지난달 물가 3.1%↑, 26개월 만에 최고 / 5월 석유류 가격 전년比 24.2%↑…소비자물가상승률 3% 넘어(종합2보) - 동일 물가 통계의 사실상 중복 편성이다.

### Improvement Hints
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- raw 후보가 충분한데 선호 카드 수(섹션당 5개)에 못 미친 섹션이 있습니다: dist(-1). 빈 5번째 슬롯에는 고품질 수급·유통 cross-fill 후보를 재검토하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 5%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
