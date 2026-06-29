## Daily Eval (2026-06-30)
- Overall: **73.22** (warn)
- Operational: **85.51**
- Reader quality: **75.52** (clear; penalty=10.0, cap=100.0, reasons=clear)
- Quality gate: **73.22** (needs_major_iteration, editorial_below_target_bounded_penalty; editorial=72.0, operational=85.5)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=73.7, section_fit=88.8, core=68.2, commodity=99.1
- Briefing cards: 20 / Commodity cards: 25
- Sections: supply:5/5 raw=193, policy:5/5 raw=81, dist:5/5 raw=40, pest:5/5 raw=12
- Metrics: title_unique=1.00, domain_diversity=0.85, summary_presence=1.00, summary_numeric=1.00, fresh_72h=1.00, fit_avg=2.95, false_positive=0.05, hard_reader_issues=0, weak_core=0.29, editorial_penalty=2.8, commodity_weak=0.00, commodity_items=6, commodity_active_today=11, commodity_active_today_unlinked=5, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.00, commodity_dominant_section=0.50, semantic_penalty=6.0


### Editorial Shadow Eval
- Editorial: **72.00** (target 95, needs_major_iteration)
- Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)
- Section count gate: 100.0 (target_met)
- Components: article_selection=70.0, section_fit=68.0, core=61.0, summary=84.0, missed=66.0, noise=63.0
- Summary: 분량과 최신성은 충족했지만, 편집 선별 품질은 목표 95와 거리가 큽니다. 특히 policy 섹션에 비농업 고속도로 기사와 유통/가격 동향 기사가 섞였고, supply에는 자동차 시장 기사가 들어가는 명백한 오탐이 있습니다. dist는 양파 대만 수출과 밀양 물류센터 유치 기사를 각각 중복적으로 싣는 바람에 가락시장 시범휴업 같은 더 중요한 유통 운영 이슈를 놓쳤습니다. pest는 원자료 풀이 약한 편이라 일부 일반 예찰/방제 기사는 허용 가능하지만, 과수화상병 확산 기사를 핵심으로 잡지 않은 점은 아쉽습니다.
- [high] irrelevant_article: 3000만원대 중 친환경차 ‘공습’…현대차 포위전략 ‘반격’ - 자동차·전기차 시장 기사로 농업 수급과 무관한 명백한 오탐입니다.
- [high] wrong_section: [민생브리핑]'성남~서초 고속도로' 추진 양재나들목 정체 줄인다 - 농업 정책이 아닌 일반 교통 인프라 기사입니다.
- [high] wrong_section: 서울청과, 애월농협과 산지 농산물 유통 활성화 협력 - 도매시장·산지 유통 협력 기사로 policy 핵심 카드에 부적합합니다.
- [high] weak_core: 정부비축 국산 콩 6만5000톤 푼다 - 정책성은 있으나 selection_fit_score가 낮고, 더 넓은 물가·수급 정책 후보가 보입니다.
- [medium] wrong_section: 늦어지는 '장마'·무더위에 농산물값, 체리·파프리카↓ , 다다기오이·... - aT 라디오 가격 동향으로 supply/시장동향 성격이 강합니다.

### Improvement Hints
- 핵심기사 품질 편차가 큽니다. core 기사에는 low-fit·tail 후보를 쓰지 말고, fit 상위권이면서 실제 이슈성이 강한 기사만 남기세요.
- 리콜 시드 결손이 보입니다: policy, pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 금융·정치성 오탐이 브리핑에 섞였습니다 (비율 5%). 제목 기준 원예·시장 실무 신호가 약한 주가·공약형 기사는 수집, 최종 선정, 품목 보드 단계에서 함께 차단하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 핵심기사 요약은 행사성 문구를 걷어내고 가격·물량·방제 같은 실제 이슈 변수를 첫 문장에 바로 둔다.
