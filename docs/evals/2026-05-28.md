## Daily Eval (2026-05-28)
- Overall: **82.00** (warn)
- Operational: **95.46**
- Quality gate: **82.00** (needs_iteration, editorial_below_target; editorial=82.0, operational=95.5)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.0, section_fit=100.0, core=100.0, commodity=96.6
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=143, policy:5/5 raw=90, dist:5/5 raw=30, pest:5/5 raw=52
- Metrics: title_unique=1.00, domain_diversity=0.95, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=5.20, false_positive=0.00, weak_core=0.00, editorial_penalty=3.2, commodity_weak=0.06, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=79.0, section_fit=83.0, core=74.0, summary=88.0, missed=80.0, noise=77.0
- Summary: 구성 수는 모두 채웠지만, 실제 기사 선택의 편집 품질은 목표치 95에 못 미친다. 공급 섹션의 1번 코어가 지역 홍보성 기사인 점이 가장 큰 감점 요인이고, 유통 섹션도 실무·시장 운영 기사보다 출하식/판촉전 비중이 높다. 병해충 섹션은 공주 신규 발생과 위기단계 격상 같은 더 강한 전국성 이슈를 코어로 세우지 못했다. 정책은 무난하나 유사한 수급점검 기사와 지역 생활물가 꼬리기사가 다소 약하다.
- [high] weak_core: 경남농기원, 우리 몸엔 역시 '신토불이 국산 양파 ' 홍보 - 지역 소비홍보성 기사로 전국 수급 코어감이 약함.
- [medium] promotional_filler: 괴산군 원원종 감자 생산 목표 초과 달성 - 보드성 성과 기사로 당일 핵심 수급 이슈와 거리 있음.
- [medium] section_miss: 계란 등 인천도 생활물가 등락...고추장·배추·오이 내린 곳도 - 지역 생활물가 스케치로 정책성 낮음.
- [medium] duplication: 농산물 물가, 맞춤형으로 대응 / 농산물 가격은 내리고 축산물은 오르고…공급 확대ㆍ할인지원, 수급 안... - 같은 정부 수급점검 회의의 유사 반복.
- [medium] weak_section_fit: 완주 삼례 농협 , 명품 흑피수박 ‘블랙위너’ 본격 출하 - 출하식·브랜드 소개 성격이 강해 유통 실무성은 제한적.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%, pest_theme_duplicate=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
