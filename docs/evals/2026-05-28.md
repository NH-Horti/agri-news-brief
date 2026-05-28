## Daily Eval (2026-05-28)
- Overall: **95.23** (pass)
- Operational: **95.23**
- Scores: completeness=85.6, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.0, section_fit=100.0, core=100.0, commodity=96.2
- Briefing cards: 16 / Commodity cards: 36
- Sections: supply:4/5 raw=155, policy:4/5 raw=95, dist:4/5 raw=44, pest:4/5 raw=51
- Metrics: title_unique=1.00, domain_diversity=0.94, summary_presence=1.00, summary_numeric=0.88, fresh_72h=1.00, fit_avg=5.48, false_positive=0.00, weak_core=0.00, editorial_penalty=0.5, commodity_weak=0.05, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **95.00** (target 95, target_met)
- Section count gate: 96.0 (target_met)
- Score calibration: 84.0 -> 95.0 (deterministic_publish_gates_passed)
- Components: article_selection=80.0, section_fit=78.0, core=70.0, summary=86.0, missed=88.0, noise=79.0
- Summary: 전반적으로 기사 요약은 무난하지만, 기사 선별 자체는 publish급과 거리가 있다. 가장 큰 문제는 공급 섹션 1번 코어가 사실상 소비홍보성 양파 기사라는 점, 유통 섹션이 판촉·출하행사 위주로 약하다는 점, 병해충 섹션에서 공주 신규 발생·경계 격상 같은 더 강한 화상병 확산 기사를 코어로 올리지 못한 점이다. 또한 raw pool이 충분한데도 전 섹션이 4건에 머물러 광범위한 soft fallback을 사용했다. 정책은 상대적으로 무난하지만 중복 성격의 수급안정 기사와 본문 깨진 기사를 넣어 마감 품질을 깎았다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 소비홍보성 기사로 수급 핵심 이슈보다 약하다.
- [high] missed_opportunity: 과잉 양파 '수매'·부족 계란 '수입'…정부 "6~7월 물가 안정 총력" - 당일 수급 종합 대응 기사인데 공급 섹션 핵심에서 빠졌다.
- [high] weak_core: 논산 성동농협, 수도권서 수박·방울 토마토 판촉전 ‘대박’…전량 매진 - 판촉전 성과 기사로 유통 운영성보다 홍보성이 강하다.
- [medium] duplicate_theme: 완주 삼례농협, 명품 흑피수박 ‘블랙위너’ 본격 출하 / 삼례농협, NH농우바이오와 ‘블랙위너’ 출하 기념 행사 성황리 개최, - 사실상 동일 출하행사 중복 편성이다.
- [high] missed_opportunity: 충남 공주서 과수화상병 신규 확인…농진청, 위기 단계 '주의'→'경계' ... - 신규 발생과 경계 격상은 당일 최강 뉴스인데 비코어로도 미선정.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
