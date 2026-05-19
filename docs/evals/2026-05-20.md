## Daily Eval (2026-05-20)
- Overall: **98.93** (pass)
- Operational: **98.93**
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=99.9, core=100.0, commodity=100.0
- Briefing cards: 16 / Commodity cards: 43
- Sections: supply:5/3 raw=150, policy:4/3 raw=95, dist:3/3 raw=56, pest:4/3 raw=64
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.56, false_positive=0.00, weak_core=0.00, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **72.00** (target 95, needs_major_iteration)
- Components: article_selection=68.0, section_fit=70.0, core=63.0, summary=83.0, missed=66.0, noise=58.0
- Summary: 핵심 이슈인 채소값 급락과 과수화상병은 잡았지만, 섹션 배치가 흔들리고 홍보성·지역기관 행사성 기사 비중이 높다. 특히 공급·유통에서 약한 코어 선택과 중복성 화상병 기사, 정책 섹션의 비정책성 가격동향 기사로 편집 판단이 아쉽다. 원시 후보군에 더 적합한 유통·정책 기사들이 보여 전반적으로는 ‘사용 가능하지만 손질 필요’ 수준이다.
- [high] wrong_section: 5월 입하 이후, 품종 교체 및 주산지 변동으로 일부 농산물 가격 오름세 - 지역 가격동향 소식지 기사로 정책성 약함.
- [high] promotional_filler: NH농협 창녕군지부, 마늘 망 지원… 농업인 영농비 절감 기대 - 지역 농협 지원행사성 기사로 전국 수급 정보가 약함.
- [medium] promotional_filler: 강원 농협 연합판매사업 협의회, 2026 산지 유통 현장투어 개최 - 벤치마킹 행사 소개 중심, 실제 유통 변화 정보 빈약.
- [medium] wrong_section: ‘블루베리’ 소득작목 육성 온힘 - 생산·품목육성 성격이 강하고 유통 구조 변화는 제한적.
- [high] duplicate_theme: 과수화상병 3건 동시 선택 - 핵심 사실이 대부분 겹쳐 섹션 효율 저하.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
