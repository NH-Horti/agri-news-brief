## Daily Eval (2026-07-09)
- Overall: **96.20** (pass)
- Operational: **96.38**
- Reader quality: **96.20** (clear; penalty=0.2, cap=100.0, reasons=clear)
- Quality gate: **96.20** (target_met, all_targets_met; editorial=88.0, operational=96.4)
- Scores: completeness=100.0, diversity=88.9, source=80.0, summary=100.0, freshness=100.0, retrieval=90.0, section_fit=100.0, core=92.6, commodity=96.1
- Briefing cards: 20 / Commodity cards: 12
- Sections: supply:5/5 raw=180, policy:5/5 raw=138, dist:5/5 raw=59, pest:5/5 raw=33
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.20, summary_presence=1.00, summary_numeric=0.90, fresh_72h=1.00, fit_avg=4.73, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.1, commodity_weak=0.00, commodity_items=7, commodity_active_today=11, commodity_active_today_unlinked=4, commodity_coverage=0.21, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.57, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **88.05** (daily target 88, tier=daily_pass, target_met)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 88.10; authoritative method=weighted_components_v1
- Acceptance: pass (blocking=0, major=0, reasons=clear)
- Section count gate: 100.0 (target_met)
- Components: article_selection=89.0, section_fit=91.0, core=87.0, summary=88.0, missed=85.0, noise=88.0
- Summary: 목표 수량은 모두 채웠고 핵심 물가·수급 이슈와 온라인도매 물류, 과수화상병 대응을 대체로 잘 잡았다. 다만 농산물 가격 폭락·물가 대응 주제가 공급/정책에 과밀하고, dist와 pest의 후순위 카드에 지역 행사·일반 관리성 기사가 섞여 편집 밀도가 조금 떨어진다. 일부 더 큰 전국 단위 후보(K-푸드+ 수출, 강서공판장 수급 점검 등)를 놓친 점과 과일 관측 요약 품질이 감점 요인이다.
- [moderate] duplicate_theme: 농산물 가격 폭락·농민 집회·정부 대응 관련 다수 카드 - 공급 2·5번과 정책 7·9번이 같은 가격 폭락 위기를 반복해 섹션 다양성이 줄었다.
- [moderate] bad_summary: 7월 과일류 농업관측 - 요약에 출처 문구와 기사 본문 절단 흔적이 남고, 생산 증가와 7월 출하 감소가 정리되지 않았다.
- [moderate] weak_core: "농자재값 폭등·농산물 가격 폭락, 이대로는 다 죽는다" - 현장 집회 기사로 시의성은 있으나 핵심 공급 카드로는 데이터성 관측·수급대책 기사보다 약하다.
- [moderate] promotional_filler: 합천유통· 사과 대추 공선 출하 회, 공동 출하 협약 …"시장 경쟁력 높여" - 10여 명 참석 지역 협약 기사로 전국 독자에게 줄 운영 정보가 제한적이다.
- [minor] weak_core: ’26년 가락시장 등 하계 휴업일 안내 - 출하 조정에 유용하지만 정례 휴업 안내라 core로는 다소 루틴성이다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: supply. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
