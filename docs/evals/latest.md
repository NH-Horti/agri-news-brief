## Daily Eval (2026-09-14)
- Overall: **85.45** (warn)
- Operational: **93.00**
- Reader quality: **87.97** (capped; penalty=5.0, cap=90.0, reasons=commodity_pool_false_link)
- Quality gate: **85.45** (needs_major_iteration, editorial_major_issue; editorial=76.9, operational=93.0)
- Scores: completeness=100.0, diversity=100.0, source=100.0, summary=100.0, freshness=92.9, retrieval=89.8, section_fit=79.5, core=98.4, commodity=94.9
- Briefing cards: 20 / Commodity cards: 37
- Sections: supply:5/5 raw=329, policy:5/5 raw=141, dist:5/5 raw=73, pest:5/5 raw=28
- Metrics: title_unique=1.00, domain_diversity=0.75, low_tier=0.15, summary_presence=1.00, summary_numeric=0.85, fresh_72h=1.00, fit_avg=3.69, false_positive=0.00, hard_reader_issues=0, weak_core=0.00, editorial_penalty=2.4, commodity_weak=0.00, commodity_items=10, commodity_active_today=22, commodity_active_today_unlinked=12, commodity_coverage=0.30, commodity_strict_link=1.00, commodity_false_link=0.00, commodity_pool_false_link=0.07, commodity_dominant_section=0.60, semantic_penalty=0.0


### Editorial Shadow Eval
- Editorial: **76.90** (daily target 82, tier=needs_major_iteration, needs_major_iteration)
- Model: gpt-5.6-sol (resolved gpt-5.6-sol)
- Model-reported score: 77.00; authoritative method=weighted_components_v1
- Acceptance: needs_iteration (blocking=0, major=1, reasons=editorial_score_min, no_major_issues, critical_components_min, all_components_min)
- Section count gate: 100.0 (target_met)
- Components: article_selection=78.0, section_fit=82.0, core=70.0, summary=90.0, missed=72.0, noise=68.0
- Summary: 형식과 기사 수, 요약 품질은 좋지만 유통 섹션의 중복·홍보성 핵심 선정과 정책·공급의 약한 꼬리 기사 때문에 편집 완성도가 낮아졌다.
- [major] duplicate_story: 가락시장, 느타리버섯·봄동·제주당근 파렛트 출하 의무화 - 바로 앞 카드와 동일한 파렛트 의무화 조치를 반복한다.
- [moderate] promotional_filler: 청주 농수산물도매시장, 옥산 이전 앞두고 '미래 유통' 담은 새 상징 공개 - BI 공개가 핵심으로 실질적인 시장 운영·물류 변화가 부족하다.
- [moderate] weak_core: 청주 농수산물도매시장, 옥산 이전 앞두고 '미래 유통' 담은 새 상징 공개 - 홍보성 BI 기사는 유통 섹션 핵심 카드로 부적절하다.
- [moderate] wrong_section: 농산물가격 안정제, 아쉬움이 큰 이유 - 가격 동향보다 제도 평가가 중심이며 정책 섹션의 동일 제도 기사와도 겹친다.
- [moderate] promotional_filler: 조지연 의원, 농식품부 장관 만나 경산 농업사업 국비 지원 요청 - 지역 의원의 예산 건의 활동으로 전국 정책 영향이나 확정성이 약하다.

### Improvement Hints
- 섹션 오배치 의심 기사가 보입니다. section-fit이 낮거나 다른 섹션에서 더 적합한 후보가 있었던 기사들을 우선 재배치하세요.
- 품목 보드 대표기사가 품목 핵심 이슈를 충분히 대변하지 못합니다. 제목에서 품목명과 수급·가격·병해충 신호가 함께 보이는 기사, representative rank 상위 후보, 비수급 섹션의 직접 이슈 후보를 우선하세요.
- 편집 품질상 약한 기사 선택이 감지되었습니다 (promotional_filler=5%). 운영 자동 피드백에는 바로 반영하지 말고, 코어 기사 demotion과 섹션별 soft penalty로 미세 조정하세요.
- 농업과 무관한 기사가 브리핑에 포함되어 있습니다 (비율 5%). 해외 경제지표, 관광 홍보, 비농업 기사가 선정되지 않도록 is_relevant 게이트를 점검하세요.

### Next Summary Feedback
- 각 기사 요약은 2문장으로 유지하고 첫 문장에 품목·지역·핵심 이슈를 바로 적는다.
- 기사에 수치가 있으면 1개 이상 남기고, 없으면 대응 주체나 시점을 분명히 적는다.
- 비슷한 시작 표현을 반복하지 말고 원인과 대응을 분리해서 간결하게 쓴다.
