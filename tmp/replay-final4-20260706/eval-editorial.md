## Daily Eval (2026-07-06)
- Overall: **90.58** (pass)
- Operational: **94.27**
- Reader quality: **94.27** (clear; penalty=0.0, cap=100.0, reasons=clear)
- Quality gate: **90.58** (needs_iteration, editorial_major_issue; editorial=83.2, operational=94.3)
- Scores: completeness=100.0, diversity=92.9, source=100.0, summary=89.5, freshness=90.0, retrieval=89.4, section_fit=95.8, core=100.0, commodity=99.8
- Briefing cards: 20 / Commodity cards: 29
- Sections: supply:5/5 raw=255, policy:5/5 raw=138, dist:5/5 raw=100, pest:5/5 raw=40
- Metrics: title_unique=1.00, domain_diversity=0.60, low_tier=0.15, summary_presence=1.00, summary_numeric=0.70, fresh_72h=1.00, fit_avg=4.23, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=0.0, commodity_weak=0.00, commodity_items=11, commodity_active_today=16, commodity_active_today_unlinked=5, commodity_coverage=0.33, commodity_strict_link=0.91, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.45, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **83.25** (daily target 88, tier=needs_iteration, needs_iteration)
- Model: gpt-5.5-2026-04-23 (resolved gpt-5.5-2026-04-23)
- Model-reported score: 84.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=2, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min, operational_score_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=84.0, section_fit=88.0, core=89.0, summary=78.0, missed=77.0, noise=80.0
- Summary: 분량은 4개 섹션 모두 5건으로 충족했고, 수급·정책의 핵심 관측/물가/농자재 기사는 대체로 적절하다. 다만 양배추 가격폭락 기사를 수급·정책에 중복 배치했고, 유통 섹션은 더 강한 공판장·산지유통 운영 기사 대신 군수 현장홍보·지역 행사성 기사 비중이 높다. 병해충도 과수화상병 현황성 핵심 후보를 놓치고 지역 방제·자문성 꼬리가 섞였다. 일부 요약에는 HTML/이미지 문구와 어색한 자동요약 흔적이 있어 독자 효용을 낮춘다.
- [major] duplicate_story: [자막뉴스] 수확 대신 폐기 선택...속 타들어 가는 농민들 / 생산비도 못 건지는 양배추 값...밭 갈아엎은 농민들 - 같은 YTN 양배추 가격폭락·밭 갈아엎기 리포트를 수급과 정책에 각각 배치했다.
- [moderate] missed_candidate: “오이 한 상자 5200원”…과채류 가격 폭락에 농가 비상 - 최근 산지 가격폭락과 농자재 부담을 다룬 강한 현장 수급 기사인데 저적합 중복/점검 기사에 밀렸다.
- [moderate] promotional_filler: 가락동도매시장 찾은 김세훈 화천군수…“농민들 정성이 제값 받게” - 가락시장 방문·지역 농산물 홍보 중심의 지방단체장 동정성 기사로 유통 운영 정보가 약하다.
- [major] missed_candidate: 햇마늘 경매 개시…“농가 제값받기 최선” - 공판장 경매 물량·경락가·출하예약제 등 유통 섹션에 더 적합한 최상위 후보가 빠졌다.
- [moderate] missed_candidate: 경북지역 조합공동사업법인, 농산물 판매확대로 농가소득 증대 앞장 - 산지조직 컨설팅·연합사업·APC 경쟁력 등 운영성이 강한 후보가 약한 로컬 홍보성 카드에 밀렸다.

### Improvement Hints
- 요약 문장 품질 편차가 큽니다. 품목·지역·수치·대응을 앞 문장에 명시하도록 프롬프트 피드백을 자동 반영하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고, 85~140자 안에서 품목·지역·핵심 변수만 남긴다.
