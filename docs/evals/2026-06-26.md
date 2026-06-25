## Daily Eval (2026-06-26)
- Overall: **82.00** (warn)
- Operational: **98.19**
- Reader quality: **86.00** (capped; penalty=2.0, cap=86.0, reasons=commodity_pool_false_link, commodity_pool_false_link_severe)
- Quality gate: **82.00** (needs_iteration, editorial_blocking_issue; editorial=82.0, operational=98.2)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=83.8, section_fit=97.2, core=100.0, commodity=98.6
- Briefing cards: 20 / Commodity cards: 30
- Sections: supply:5/5 raw=160, policy:5/5 raw=110, dist:5/5 raw=59, pest:5/5 raw=32
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=4.28, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=10, commodity_active_today=14, commodity_active_today_unlinked=4, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.15, commodity_dominant_section=0.50, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **82.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=80.0, section_fit=81.0, core=83.0, summary=91.0, missed=76.0, noise=79.0
- Summary: 구성 수와 최신성은 좋고 핵심 이슈도 일부 잘 잡았지만, 기사 선택 자체는 아쉬움이 분명하다. 공급은 사설성 마늘 기사와 지역 출하 홍보가 섞였고, 정책은 포럼·기자회견 중심으로 실제 집행 정책보다 약하다. 유통은 온라인도매시장 3건이 사실상 중복인데도 더 강한 양파 톤백/APC 운영, 가락시장 운영 변경 같은 실무형 후보를 놓쳤다. 병해충은 화상병 코어는 적절하지만 지역 확산 기사 중복성이 높고 비병해충성 장마 피해 예방 기사를 넣은 점이 감점 요인이다.
- [high] weak_core: 기후재앙 맞은 마늘 산업, 신속한 시장격리와 소비자 온정 모을 때 - 사설 성격이 강해 사실 기사보다 주장 비중이 크다.
- [high] promotional_filler: 예천 복숭아 본격 출하… 전국 소비자 식탁 찾는다 - 지역 출하 홍보성으로 전국 수급 정보가 약하다.
- [high] missed_opportunity: 정부 비축 국산 콩 6.5만톤 푼다…식품업계 원료 수급 안정 지원 - 실행형 수급정책 후보가 있었는데 미선정됐다.
- [medium] weak_selection: 주요 농산물 공공수급제 실시, 반값 농자재를 보장하라 - 요구성 기자회견으로 정책 진전 정보가 제한적이다.
- [high] duplication: 영동 거봉 포도 온라인 산지경매 관련 3건 동시 선택 - 같은 이벤트를 3건 반복해 지면 효율이 떨어진다.

### Improvement Hints
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 리콜 시드 결손이 보입니다: policy, dist. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
