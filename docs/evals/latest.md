## Daily Eval (2026-06-22)
- Overall: **96.41** (pass)
- Operational: **97.51**
- Reader quality: **97.51** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **96.41** (needs_iteration, editorial_below_target_bounded_penalty; editorial=84.0, operational=97.5)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=94.3, retrieval=88.8, section_fit=100.0, core=90.6, commodity=97.5
- Briefing cards: 20 / Commodity cards: 47
- Sections: supply:5/5 raw=238, policy:5/5 raw=242, dist:5/5 raw=70, pest:5/5 raw=82
- Metrics: title_unique=1.00, domain_diversity=0.75, summary_presence=1.00, summary_numeric=0.80, fresh_72h=1.00, fit_avg=5.33, false_positive=0.00, hard_reader_issues=0, weak_core=0.12, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=13, commodity_active_today=17, commodity_active_today_unlinked=4, commodity_coverage=0.39, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.54, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **84.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=82.0, section_fit=86.0, core=84.0, summary=90.0, missed=78.0, noise=83.0
- Summary: 전반적으로 5x4 구성을 채우고 큰 오분류는 많지 않지만, 공급 섹션에서 경남 마늘·양파류의 중복/지역 편중이 심하고, 유통 섹션은 운영 기사보다 농협 성공사례·개장 안내 성격이 섞여 핵심도가 약해졌다. 병해충은 화상병 중심 편성은 맞지만 더 강한 보은·충북 확산 기사 풀이 보였는데 지역 단신·일반 관리성 기사가 포함돼 아쉽다. 정책은 비교적 안정적이나 비료 예산 기사 채택으로 더 직접적인 수급·물가 대응 후보를 일부 놓쳤다.
- [high] duplication: 생산비도 못 건지는 남해 마늘 가격…농민들 "가격안정" 요구 - 같은 섹션에 경남 마늘·양파 고충 기사 3건이 겹친다.
- [medium] duplication: 마늘은 녹고 양파 는 갈아엎고… 경남 농가 덮친 '이상기후·공급과잉' 이... - 연합 기사와 내용축이 매우 유사한 지역 재가공 기사다.
- [medium] wrong_section_bias: 공선회·APC 운영 활성화…판매사업 날개 - 유통 실무성은 있으나 농협 성공사례 성격이 강해 대표 핵심으로는 다소 홍보성이다.
- [medium] weak_core: 여름 배추 경매 1시간 앞당긴다 - 실무적으로 유효하지만 파급력이 제한적이고 선택 점수도 낮다.
- [medium] promotional_filler: 통합 첫 시험대 오른 영산 마늘 경매장…창녕남부농협, 7월 1일 첫 경매 - 개장 안내와 기관 계획 위주로 독자 효용이 약하다.

### Improvement Hints
- 전반적으로 안정적입니다. 점수 추세가 3일 이상 하락할 때만 임계치 조정이나 query 보강을 수행하면 됩니다.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
