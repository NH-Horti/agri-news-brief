## Daily Eval (2026-05-18)
- Overall: **97.15** (pass)
- Operational: **97.15**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=90.0, retrieval=85.0, section_fit=99.9, core=100.0, commodity=95.4
- Briefing cards: 16 / Commodity cards: 60
- Sections: supply:4/3 raw=207, policy:4/3 raw=113, dist:3/3 raw=33, pest:5/3 raw=65
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.75, fresh_72h=1.00, fit_avg=4.42, false_positive=0.00, weak_core=0.00, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **78.00** (target 95, needs_major_iteration)
- Components: article_selection=74.0, section_fit=79.0, core=72.0, summary=86.0, missed=68.0, noise=73.0
- Summary: 형식은 갖췄지만 기사 고르기가 보수적이고 중복·홍보성 선택이 섞였다. 특히 공급은 핵심 이슈인 양파 가격 폭락·정부 수급대응보다 제주 마늘 현장 스케치가 1순위 코어로 올라 약하다. 유통은 블루베리 육성사업이 조합 홍보성에 가깝고, 병해충은 같은 과수화상병 첫 발생 기사 중복이 과하다. 정책은 산란계협회 제재는 좋았지만 나머지 축은 상대적으로 힘이 떨어진다.
- [high] weak_core: “작황 아쉽지만 값 잘 받았으면”…제주 남도종 마늘 수확 현장 - 현장 스케치 성격이 강해 전국 수급 이슈 대표성이 약함.
- [high] duplication: 양파 갈아엎기 기사 2건 동시 선정 - 같은 사건을 공급 섹션에 중복 배치해 지면 효율이 떨어짐.
- [medium] section_mismatch: 가락시장, 근교산 채소·햇감자 파렛트 운송지원 확대 추진 - 물류·시장 운영 성격이 강해 유통 섹션이 더 자연스러움.
- [high] promotional: 서익산 농협 , 블루베리 육성사업으로 농가소득 견인 - 조합 성과 소개 중심의 홍보성 기사로 유통 현안성이 낮음.
- [medium] weak_selection: 가락시장 유통인, "시설현대화 국비 지원 확대·융자 금리 인하" 촉구 - 이해관계자 요구 기사로 정책 확정·제도 변화 정보가 제한적.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
