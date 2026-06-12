## Daily Eval (2026-06-12)
- Overall: **86.00** (pass)
- Operational: **97.65**
- Reader quality: **97.29** (clear; penalty=0.4, cap=100.0, reasons=clear)
- Quality gate: **86.00** (needs_iteration, editorial_below_target; editorial=86.0, operational=97.7)
- Scores: completeness=100.0, diversity=100.0, summary=100.0, freshness=100.0, retrieval=85.2, section_fit=100.0, core=91.8, commodity=92.0
- Briefing cards: 20 / Commodity cards: 14
- Sections: supply:5/5 raw=205, policy:5/5 raw=75, dist:5/5 raw=44, pest:5/5 raw=25
- Metrics: title_unique=1.00, domain_diversity=0.70, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.48, false_positive=0.00, hard_reader_issues=0, weak_core=0.17, editorial_penalty=0.2, commodity_weak=0.00, commodity_items=6, commodity_coverage=0.18, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_dominant_section=0.67, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **86.00** (target 95, needs_iteration)
- Section count gate: 100.0 (target_met)
- Components: article_selection=85.0, section_fit=84.0, core=90.0, summary=93.0, missed=80.0, noise=82.0
- Summary: 기본 골격과 핵심 이슈 포착은 좋다. 공급의 양파·배추, 병해충의 과수화상병은 적절했고 유통도 공판장·저온유통체계 등 운영성 있는 기사들이 섞였다. 다만 정책 섹션의 후순위 카드들이 약하고, 제주 공약성 기사와 당진 환기창 지원처럼 정책 핵심성이 떨어지는 항목이 들어가 점수를 깎는다. 공급 섹션도 매실 지원성 지역 기사 비중이 높아 더 강한 전국·산업 구조 기사 활용 여지가 있었다. 유통은 5장을 채웠지만 고창수박 출하식 같은 프로모션성 카드가 포함돼 품질이 살짝 흔들린다. 전반적으로 90점대 초반까지는 가능하지만, 잘 보이는 대체 후보를 놓치고 지역성·홍보성 꼬리를 다소 허용해 95점급은 아니다.
- [high] wrong_section_or_weak_policy: 농산물 유통공사·도민 펀드…“농산물 경쟁력 높여야” - 제주 당선인 공약 해설은 정책 확정성 낮고 지역 공약성 기사다.
- [medium] weak_tail: 시설하우스 ‘천장 환기창’ 달아 폭염 극복 - 현장 지원 사례로는 유용하지만 정책면 핵심 의제성은 약하다.
- [medium] weak_tail: 정부, 무기질비료 보조금 '115억' 긴급 투입 - 나쁘진 않지만 단신성 지원기사로 정책면 무게감이 약하다.
- [medium] promotional_filler: 대한민국 대표 여름 과일 '고창수박' 본격 출하 …전국 소비자 입맛 공략 - 출하식·시장 공략형 홍보 기사 성격이 강하다.
- [medium] section_quality_mix: 광양시, ' 매실 상생마케팅 후원금' 2000만 원 지원…소비촉진·제값받기... - 소비촉진 후원금 중심의 지역 지원 기사로 공급 핵심성은 제한적이다.

### Improvement Hints
- 리콜 시드 결손이 보입니다: pest. query seed 보강 또는 Google/HF 보조 리콜을 검토하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=10%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
