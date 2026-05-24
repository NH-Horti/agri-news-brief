## Daily Eval (2026-05-22)
- Overall: **95.91** (pass)
- Operational: **95.91**
- Scores: completeness=89.2, diversity=100.0, summary=100.0, freshness=100.0, retrieval=86.9, section_fit=100.0, core=99.3, commodity=95.2
- Briefing cards: 17 / Commodity cards: 43
- Sections: supply:4/5 raw=158, policy:4/5 raw=167, dist:4/5 raw=52, pest:5/5 raw=43
- Metrics: title_unique=1.00, domain_diversity=0.71, summary_presence=1.00, summary_numeric=0.94, fresh_72h=1.00, fit_avg=4.44, false_positive=0.00, weak_core=0.00, editorial_penalty=0.6, commodity_weak=0.00, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **88.00** (target 95, needs_iteration)
- Section count gate: 97.0 (target_met)
- Components: article_selection=87.0, section_fit=89.0, core=90.0, summary=92.0, missed=84.0, noise=86.0
- Summary: 핵심 이슈인 양파 수급난, 가격안정제 시행, 과수화상병 경계 상향은 잘 잡았다. 다만 공급·정책·유통이 모두 4건에 그쳐 원시 후보 풀이 충분한 날치고는 섹션 완성도가 떨어지고, 일부 꼬리 카드가 약했다. 특히 공급의 자두 출하, 정책의 지역의원 농자재 지원안은 전국 단위 브리프 기준으로 우선순위가 낮다. 유통은 물류·수출 대응을 담았지만 시세 카드와 중동 수출 카드가 섞이며 운영·물류 축의 선명도가 조금 흐려졌다. 전반적으로 사용 가능하지만, 95점 목표에는 못 미친다.
- [medium] underfill: 섹션 4건만 편성 - 원시 후보가 충분한데 5건을 채우지 못했다.
- [high] weak_tail: 경산 와촌 시설재배 자두 (정상) 본격 출하 - 단순 출하 소식으로 수급 이슈성·전국성이 약하다.
- [medium] underfill: 섹션 4건만 편성 - 원시 후보가 충분한데 5건 목표를 못 채웠다.
- [high] weak_tail: 생산비 폭등에 농민은 빚더미…장진영 의원, 필수 농자재 직접지원 추진 - 지역 의원 발의성 기사로 전국 정책 임팩트가 약하다.
- [medium] underfill: 섹션 4건만 편성 - 유통 후보가 적지 않은데 5건 구성이 가능했다.

### Improvement Hints
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=6%, pest_theme_duplicate=6%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
