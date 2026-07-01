import unittest
from pathlib import Path

import report_eval
from scripts.evaluate_daily_report import apply_editorial_quality_gate


ROOT = Path(__file__).resolve().parents[1]


class ReportEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report_date = "2026-04-10"
        cls.html_text = (ROOT / "docs" / "archive" / f"{cls.report_date}.html").read_text(encoding="utf-8")
        cls.snapshot_payload = report_eval.load_snapshot_payload(
            ROOT / "docs" / "replay" / f"{cls.report_date}.snapshot.json"
        )

    @staticmethod
    def _briefing_card(section: str, title: str, href: str, *, core: bool = False, stage: str = "tail") -> str:
        core_attr = ' data-is-core="1"' if core else ""
        badge = '<span class="badgeCore">핵심</span>' if core else ""
        return f"""
        <div
          data-surface="briefing_card"
          data-section="{section}"
          data-article-title="{title}"
          data-href="{href}"
          data-article-id="{href}"
          data-target-domain="example.com"
          data-selection-fit="1.6"
          data-selection-stage="{stage}"
          {core_attr}
        >
          {badge}
          <div class="sum">{title} 관련 수급과 현장 변화가 보고됐다.</div>
        </div>
        """

    def test_parse_report_html_extracts_briefing_cards_and_summaries(self) -> None:
        articles = report_eval.parse_report_html(self.html_text)
        briefing = [article for article in articles if article.surface == report_eval.BRIEFING_SURFACE]
        commodity = [article for article in articles if article.surface in report_eval.COMMODITY_SURFACES]

        self.assertEqual(len(briefing), 15)
        self.assertGreater(len(commodity), 20)
        self.assertTrue(any(article.is_core for article in briefing))
        self.assertTrue(all(article.summary.strip() for article in briefing))

    def test_editorial_quality_gate_applies_bounded_penalty_below_target(self) -> None:
        result = {
            "overall_score": 98.13,
            "operational_score": 98.13,
            "status": "pass",
            "score_notes": {},
        }
        editorial = {
            "status": "success",
            "score": 80.0,
            "target_score": 95.0,
            "target_status": "needs_major_iteration",
        }

        apply_editorial_quality_gate(result, editorial)

        self.assertEqual(result["overall_score"], 96.63)
        self.assertEqual(result["operational_score"], 98.13)
        self.assertEqual(result["status"], "pass")
        self.assertEqual(result["quality_gate"]["reason"], "editorial_below_target_bounded_penalty")
        self.assertEqual(result["quality_gate"]["bounded_penalty"], 1.5)
        rendered = report_eval.render_evaluation_markdown(
            {
                **result,
                "report_date": "2026-05-28",
                "counts": {"briefing_by_section": {}, "raw_by_section": {}, "expected_briefing_by_section": {}},
                "metrics": {},
                "scores": {},
            }
        )
        self.assertIn("Quality gate", rendered)

    def test_editorial_quality_gate_hard_caps_blocking_issues(self) -> None:
        result = {
            "overall_score": 98.13,
            "operational_score": 98.13,
            "status": "pass",
            "score_notes": {},
        }
        editorial = {
            "status": "success",
            "score": 80.0,
            "target_score": 95.0,
            "target_status": "needs_major_iteration",
            "issues": [{"severity": "high", "type": "false_positive"}],
        }

        apply_editorial_quality_gate(result, editorial)

        self.assertEqual(result["overall_score"], 80.0)
        self.assertEqual(result["status"], "warn")
        self.assertEqual(result["quality_gate"]["reason"], "editorial_blocking_issue")
        self.assertEqual(result["quality_gate"]["blocking_issue_count"], 1)

    def test_editorial_quality_gate_treats_section_judgment_as_bounded_feedback(self) -> None:
        result = {
            "overall_score": 98.13,
            "operational_score": 98.13,
            "status": "pass",
            "score_notes": {},
        }
        editorial = {
            "status": "success",
            "score": 80.0,
            "target_score": 95.0,
            "target_status": "needs_major_iteration",
            "issues": [{"severity": "high", "type": "wrong_section"}],
        }

        apply_editorial_quality_gate(result, editorial)

        self.assertEqual(result["overall_score"], 96.63)
        self.assertEqual(result["quality_gate"]["reason"], "editorial_below_target_bounded_penalty")
        self.assertEqual(result["quality_gate"]["blocking_issue_count"], 0)

    def test_parse_report_html_extracts_commodity_primary_metadata(self) -> None:
        html = """
        <a
          data-surface="commodity_primary"
          data-section="supply"
          data-article-title="양파 가격 폭락 우려"
          data-article-id="abc123"
          data-target-domain="example.com"
          data-item-key="onion"
          data-item-label="양파"
          data-representative-rank="4"
          data-representative-score="123.4"
          data-board-score="88.2"
          data-selection-fit="1.55"
          data-selection-stage="core_final"
          data-is-core="1"
          href="https://example.com/onion-core"
        >link</a>
        """

        articles = report_eval.parse_report_html(html)
        self.assertEqual(len(articles), 1)
        article = articles[0]
        self.assertEqual(article.item_key, "onion")
        self.assertEqual(article.item_label, "양파")
        self.assertEqual(article.representative_rank, 4)
        self.assertAlmostEqual(article.selection_fit_score, 1.55)
        self.assertEqual(article.selection_stage, "core_final")
        self.assertTrue(article.is_core)

    def test_parse_commodity_board_counts_extracts_audit_metadata(self) -> None:
        html = """
        <section
          id="commodity-board"
          data-active-total="3"
          data-active-today-total="5"
          data-active-today-unlinked-total="2"
          data-managed-unlinked-total="30"
        ></section>
        """

        counts = report_eval.parse_commodity_board_counts(html)

        self.assertEqual(counts["active_total"], 3)
        self.assertEqual(counts["active_today_total"], 5)
        self.assertEqual(counts["active_today_unlinked_total"], 2)
        self.assertEqual(counts["managed_unlinked_total"], 30)

    def test_parse_report_html_extracts_briefing_selection_metadata(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="supply"
          data-article-title="양파 가격 폭락 우려"
          data-href="https://example.com/onion-core"
          data-article-id="brief123"
          data-target-domain="example.com"
          data-selection-fit="1.72"
          data-selection-stage="core_final"
          data-is-core="1"
        >
          <span class="badgeCore">핵심</span>
          <div class="sum">양파 가격과 산지 출하 조절을 다룬 기사다.</div>
        </div>
        """

        article = report_eval.parse_report_html(html)[0]

        self.assertTrue(article.is_core)
        self.assertAlmostEqual(article.selection_fit_score, 1.72)
        self.assertEqual(article.selection_stage, "core_final")

    def test_evaluate_report_returns_scores_and_feedback(self) -> None:
        result = report_eval.evaluate_report(self.report_date, self.html_text, self.snapshot_payload)

        self.assertEqual(result["counts"]["briefing_total"], 15)
        self.assertIn("commodity_active_today_unlinked_total", result["counts"])
        self.assertIn("commodity_active_today_unlinked_total", result["metrics"])
        self.assertIn(result["status"], {"pass", "warn", "fail"})
        self.assertGreaterEqual(result["overall_score"], 0.0)
        self.assertLessEqual(result["overall_score"], 100.0)
        self.assertTrue(result["improvement_hints"])
        self.assertTrue(result["summary_prompt_feedback"])
        self.assertIn("selection_guardrails", result)
        self.assertIn("summary_quality", result["scores"])
        self.assertIn("section_alignment", result["scores"])
        self.assertIn("core_quality", result["scores"])
        self.assertIn("commodity_board_quality", result["scores"])
        self.assertIn("reader_quality", result["scores"])
        self.assertIn("operational_score", result)
        self.assertIn("reader_quality_score", result)
        self.assertIn("reader_quality_gate", result)
        self.assertIn("soft_fallback_briefing_by_section", result["counts"])
        self.assertIn("minimum_fallback_briefing_by_section", result["counts"])

    def test_expected_briefing_count_prefers_five_with_adaptive_fallbacks(self) -> None:
        self.assertEqual(report_eval._expected_briefing_count(20), 5)
        self.assertEqual(report_eval._expected_briefing_count(5), 5)
        self.assertEqual(report_eval._expected_briefing_count(4), 4)
        self.assertEqual(report_eval._expected_briefing_count(3), 3)
        self.assertEqual(report_eval._soft_fallback_briefing_count(20), 4)
        self.assertEqual(report_eval._minimum_fallback_briefing_count(20), 3)

    def test_evaluate_report_flags_section_core_and_commodity_risks(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="supply"
          data-article-title="화천농협, 양파 공선출하회 총회·재배기술교육 펼쳐"
          data-href="https://example.com/onion-training"
          data-article-id="brief-1"
          data-target-domain="example.com"
        >
          <span class="badgeCore">핵심</span>
          <div class="sum">양파 농가 교육과 총회 소식을 전한 행사성 기사다.</div>
        </div>
        <div
          data-surface="briefing_card"
          data-section="dist"
          data-article-title="가락시장 사과 반입 감소…경락가 상승"
          data-href="https://example.com/apple-market"
          data-article-id="brief-2"
          data-target-domain="example.com"
        >
          <div class="sum">사과 반입 감소와 경락가 상승 흐름을 정리했다.</div>
        </div>
        <a
          data-surface="commodity_primary"
          data-section="supply"
          data-article-title="화천농협, 양파 공선출하회 총회·재배기술교육 펼쳐"
          data-article-id="commodity-1"
          data-target-domain="example.com"
          data-item-key="onion"
          data-item-label="양파"
          data-representative-rank="0"
          data-representative-score="58.2"
          data-board-score="46.0"
          data-selection-fit="0.45"
          data-selection-stage="tail"
          href="https://example.com/onion-training"
        >대표</a>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-04-10T08:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "화천농협, 양파 공선출하회 총회·재배기술교육 펼쳐",
                        "link": "https://example.com/onion-training",
                        "description": "양파 재배 농가 교육과 총회를 진행한 행사 기사다.",
                        "selection_fit_score": 0.45,
                        "selection_stage": "tail",
                        "score": 32.0,
                        "pub_dt_kst": "2026-04-10T06:00:00+09:00",
                    },
                    {
                        "section": "supply",
                        "title": "양파 가격 폭락 우려…산지 출하 조절·수급 대책 촉구",
                        "link": "https://example.com/onion-issue",
                        "description": "양파 가격 급락과 산지 출하 조절, 수급 대책 요구를 다룬 기사다.",
                        "selection_fit_score": 1.72,
                        "selection_stage": "core_final",
                        "score": 91.0,
                        "pub_dt_kst": "2026-04-10T05:00:00+09:00",
                    },
                ],
                "policy": [],
                "dist": [
                    {
                        "section": "dist",
                        "title": "화천농협, 양파 공선출하회 총회·재배기술교육 펼쳐",
                        "link": "https://example.com/onion-training-dist",
                        "description": "도매시장 반입과 가격 대응 문맥에서는 더 적합한 제목으로 재분류될 수 있다.",
                        "selection_fit_score": 1.6,
                        "selection_stage": "cross_section_dist_backfill",
                        "score": 83.0,
                        "pub_dt_kst": "2026-04-10T06:30:00+09:00",
                    },
                    {
                        "section": "dist",
                        "title": "가락시장 사과 반입 감소…경락가 상승",
                        "link": "https://example.com/apple-market",
                        "description": "가락시장 사과 반입 감소와 경락가 상승 흐름을 다뤘다.",
                        "selection_fit_score": 1.42,
                        "selection_stage": "core_final",
                        "score": 88.0,
                        "pub_dt_kst": "2026-04-10T04:00:00+09:00",
                    },
                ],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-04-10", html, snapshot_payload)

        self.assertLess(result["scores"]["section_alignment"], 75.0)
        self.assertLess(result["scores"]["core_quality"], 70.0)
        self.assertLess(result["scores"]["commodity_board_quality"], 65.0)
        selection_feedback = report_eval.build_selection_feedback_payload(result)
        self.assertEqual(selection_feedback["selection_guardrails"]["commodity_active_min_rank"], 2)
        self.assertTrue(selection_feedback["selection_guardrails"]["commodity_require_issue_signal"])
        self.assertTrue(selection_feedback["selection_guardrails"]["commodity_require_direct_item_focus"])
        self.assertTrue(any("섹션 오배치" in hint for hint in result["improvement_hints"]))
        self.assertTrue(any("핵심기사 품질" in hint for hint in result["improvement_hints"]))
        self.assertTrue(any("품목 보드 대표기사" in hint for hint in result["improvement_hints"]))

    def test_evaluate_report_flags_semantic_false_positive_news(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="supply"
          data-article-title="오이 솔루션, 장중 상한가 직행 후 이탈…광통신 기대감에"
          data-href="https://www.cbci.co.kr/news/articleView.html?idxno=572803"
          data-article-id="cbci-stock"
          data-target-domain="cbci.co.kr"
        >
          <div class="sum">오이솔루션 주가와 광통신 기대감을 다룬 증권 기사다.</div>
        </div>
        <div
          data-surface="briefing_card"
          data-section="dist"
          data-article-title="영등포 지도가 바뀐다... 김종길 의원, ‘영등포구청역~ 청과 시장 ’ 1호..."
          data-href="https://www.dnews.co.kr/uhtml/view.jsp?idxno=202605071103059370818"
          data-article-id="dnews-pledge"
          data-target-domain="dnews.co.kr"
        >
          <div class="sum">청과시장 일대 개발 공약을 발표한 정치 기사다.</div>
        </div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-05-08T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "오이 솔루션, 장중 상한가 직행 후 이탈…광통신 기대감에",
                        "link": "https://www.cbci.co.kr/news/articleView.html?idxno=572803",
                        "description": "오이솔루션 주가와 광통신 장비 기대감을 다룬 증권 기사다. 페이지 하단에 가락시장 종사자와 농산물 기사 목록이 섞였다.",
                        "selection_fit_score": 1.9,
                        "selection_stage": "supply_board_bridge",
                        "score": 11.68,
                        "pub_dt_kst": "2026-05-07T12:00:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [
                    {
                        "section": "dist",
                        "title": "영등포 지도가 바뀐다... 김종길 의원, ‘영등포구청역~ 청과 시장 ’ 1호...",
                        "link": "https://www.dnews.co.kr/uhtml/view.jsp?idxno=202605071103059370818",
                        "description": "국민의힘 김종길 의원이 재선 도전을 앞두고 제1호 공약으로 영등포청과시장 일대 용적률 1000% 개발과 대단지 조성을 발표했다.",
                        "selection_fit_score": 1.14,
                        "selection_stage": "underfill",
                        "score": 17.76,
                        "pub_dt_kst": "2026-05-07T11:03:00+09:00",
                    }
                ],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-05-08", html, snapshot_payload)

        self.assertEqual(result["metrics"]["content_false_positive_rate"], 1.0)
        reasons = {sample["reason"] for sample in result["content_false_positive_samples"]}
        self.assertIn("finance_company_noise", reasons)
        self.assertIn("political_market_pledge_noise", reasons)
        self.assertLess(result["overall_score"], 85.0)
        self.assertIn("semantic_false_positive", result["selection_guardrails"]["driver_tags"])
        self.assertTrue(any("금융·정치성 오탐" in hint for hint in result["improvement_hints"]))

    def test_evaluate_report_flags_policy_housing_market_false_positive(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="policy"
          data-article-title="서울 아파트값 상승에 주택시장 규제 완화 논의"
          data-href="https://example.com/housing-market"
          data-article-id="housing-market"
          data-target-domain="example.com"
        >
          <div class="sum">주택시장 규제 완화와 아파트 매매 흐름을 다룬 기사다.</div>
        </div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-06-11T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [],
                "policy": [
                    {
                        "section": "policy",
                        "title": "서울 아파트값 상승에 주택시장 규제 완화 논의",
                        "link": "https://example.com/housing-market",
                        "description": "아파트 매매가와 재건축 규제 완화가 핵심인 부동산 기사다.",
                        "selection_fit_score": 1.4,
                        "selection_stage": "tail",
                        "score": 55.0,
                        "pub_dt_kst": "2026-06-11T05:00:00+09:00",
                    }
                ],
                "dist": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-06-11", html, snapshot_payload)

        self.assertEqual(result["metrics"]["content_false_positive_rate"], 1.0)
        self.assertEqual(result["content_false_positive_samples"][0]["reason"], "housing_market_noise")

    def test_reader_quality_caps_hard_offtopic_articles(self) -> None:
        titles_by_section = {
            "supply": [
                "창녕 양파 가격 하락에 수확 농가 부담 커져",
                "준고랭지 여름 배추 시범사업으로 수급 안정",
                "성주 참외 본격 출하…산지 가격 안정 기대",
                "마늘 재배면적 감소에 산지 수급 점검",
                "분리막·동박 가격반등…K배터리 소재 온기 확산",
            ],
            "policy": [
                "농산물 가격안정제 도입 논의 본격화",
                "농식품부, 원예농산물 수급 안정 대책 점검",
                "정부, 양파·마늘 계약재배 확대 추진",
                "농가 경영안정 지원 예산 확대 논의",
                "조타실 CCTV 의무화·AI 도입…여객선 안전 대전환",
            ],
            "dist": [
                "가락시장 물류 개선으로 농산물 반입 처리 속도 높인다",
                "고당도 수박 본격 출하…도매시장 거래 활발",
                "청도 농협공판장 개장…복숭아 출하 확대",
                "제주 농산물 저온유통체계 구축 추진",
                "온라인 도매시장 농산물 거래 품목 확대",
            ],
            "pest": [
                "과수화상병 확산 비상…사과농가 긴급 예찰",
                "토마토뿔나방 방제 대응 강화",
                "장마철 고추 탄저병 예찰 당부",
                "배 과원 병해충 방제 약제 지원",
                "시설채소 병해충 발생 증가에 현장 점검",
            ],
        }
        html = "\n".join(
            self._briefing_card(section, title, f"https://example.com/{section}-{idx}", core=(idx == 0), stage="core" if idx == 0 else "tail")
            for section, titles in titles_by_section.items()
            for idx, title in enumerate(titles)
        )
        raw_by_section = {section: [] for section in report_eval.SECTION_KEYS}
        for section, titles in titles_by_section.items():
            for idx, title in enumerate(titles):
                raw_by_section[section].append(
                    {
                        "section": section,
                        "title": title,
                        "link": f"https://example.com/{section}-{idx}",
                        "description": title,
                        "selection_fit_score": 1.6,
                        "selection_stage": "core" if idx == 0 else "tail",
                        "score": 90.0,
                        "pub_dt_kst": "2026-06-12T05:00:00+09:00",
                    }
                )

        result = report_eval.evaluate_report(
            "2026-06-12",
            html,
            {"window": {"end_kst": "2026-06-12T06:00:00+09:00"}, "raw_by_section": raw_by_section},
        )

        self.assertGreater(result["operational_score"], result["overall_score"])
        self.assertLessEqual(result["overall_score"], 80.0)
        self.assertEqual(result["metrics"]["reader_hard_issue_count"], 2)
        self.assertEqual(result["reader_quality_gate"]["status"], "capped")
        reasons = {sample["reason"] for sample in result["reader_hard_issue_samples"]}
        self.assertIn("industrial_material_market_noise", reasons)
        self.assertIn("non_agri_transport_policy_noise", reasons)

    def test_commodity_board_quality_penalizes_weak_title_linkage(self) -> None:
        html = """
        <a
          data-surface="commodity_primary"
          data-section="supply"
          data-article-title="NH농우바이오·팜한농 6월 추천 품종은"
          data-article-id="zucchini-weak"
          data-target-domain="example.com"
          data-item-key="zucchini"
          data-item-label="애호박(쥬키니)"
          data-representative-rank="3"
          data-representative-score="125.0"
          data-board-score="95.0"
          data-selection-fit="1.6"
          data-selection-stage="core"
          href="https://example.com/zucchini-variety"
        >대표</a>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-06-11T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "NH농우바이오·팜한농 6월 추천 품종은",
                        "link": "https://example.com/zucchini-variety",
                        "description": "추천 품종 소개 말미에 애호박과 쥬키니 품종을 언급하지만 가격·수급 이슈는 약하다.",
                        "selection_fit_score": 1.6,
                        "selection_stage": "core",
                        "score": 80.0,
                        "pub_dt_kst": "2026-06-11T05:00:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-06-11", html, snapshot_payload)

        self.assertLess(result["scores"]["commodity_board_quality"], 65.0)
        self.assertEqual(result["metrics"]["commodity_primary_strict_link_rate"], 0.0)
        self.assertEqual(result["metrics"]["commodity_primary_false_link_rate"], 1.0)
        self.assertAlmostEqual(result["metrics"]["commodity_board_coverage_rate"], round(1 / report_eval.MANAGED_COMMODITY_EVAL_ITEM_COUNT, 4))
        self.assertEqual(result["commodity_primary_linkage_samples"][0]["item_label"], "애호박(쥬키니)")

    def test_commodity_pool_sports_homonym_penalizes_visible_false_link(self) -> None:
        title = "슈팅수 30-2…개최국 캐나다, ‘2명 퇴장’ 자멸한 카타르 6대0 대파"
        html = f"""
        <a
          data-surface="commodity_pool"
          data-section="supply"
          data-article-title="{title}"
          data-article-id="sports-green-onion-homonym"
          data-target-domain="chosun.com"
          data-item-key="green_onion"
          data-item-label="대파"
          data-representative-rank="1"
          data-representative-score="210.6"
          data-board-score="176.6"
          data-selection-fit="1.05"
          data-selection-stage="commodity_pool"
          href="https://www.chosun.com/sports/sports_special/2026/06/19/3ZUCNKZI25AJFHG6PU5KWFFF54/"
        >대파 대표 기사</a>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-06-22T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": title,
                        "link": "https://www.chosun.com/sports/sports_special/2026/06/19/3ZUCNKZI25AJFHG6PU5KWFFF54/",
                        "description": "축구 경기에서 개최국 캐나다가 카타르를 크게 이겼다는 스포츠 기사다.",
                        "selection_fit_score": 1.05,
                        "selection_stage": "commodity_pool",
                        "score": 7.8,
                        "pub_dt_kst": "2026-06-19T12:00:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-06-22", html, snapshot_payload)

        self.assertEqual(result["counts"]["commodity_pool_total"], 1)
        self.assertEqual(result["metrics"]["commodity_primary_false_link_rate"], 0.0)
        self.assertEqual(result["metrics"]["commodity_pool_false_link_rate"], 1.0)
        self.assertIn("commodity_pool_false_link_severe", result["reader_quality_gate"]["reasons"])
        self.assertIn("commodity_board", result["selection_guardrails"]["driver_tags"])
        sample = result["commodity_pool_linkage_samples"][0]
        self.assertEqual(sample["surface"], "commodity_pool")
        self.assertIn("green_onion_sports_homonym", sample["reasons"])

    def test_commodity_board_strict_link_accepts_weather_and_field_issue_terms(self) -> None:
        html = """
        <a
          data-surface="commodity_primary"
          data-section="supply"
          data-article-title="폭염에 밀리는 여름 배추…준고랭지 재배 확대"
          data-article-id="cabbage-heat"
          data-target-domain="example.com"
          data-item-key="napa_cabbage"
          data-item-label="배추"
          data-representative-rank="3"
          data-representative-score="125.0"
          data-board-score="95.0"
          data-selection-fit="1.6"
          data-selection-stage="core"
          href="https://example.com/cabbage-heat"
        >대표</a>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-06-11T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "폭염에 밀리는 여름 배추…준고랭지 재배 확대",
                        "link": "https://example.com/cabbage-heat",
                        "description": "폭염 대응을 위해 배추 재배지를 조정하는 기사다.",
                        "selection_fit_score": 1.6,
                        "selection_stage": "core",
                        "score": 80.0,
                        "pub_dt_kst": "2026-06-11T05:00:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-06-11", html, snapshot_payload)

        self.assertEqual(result["metrics"]["commodity_primary_strict_link_rate"], 1.0)
        self.assertEqual(result["metrics"]["commodity_primary_false_link_rate"], 0.0)
        self.assertEqual(result["commodity_primary_linkage_samples"], [])

    def test_commodity_board_alias_accepts_green_onion_companion_label(self) -> None:
        html = """
        <a
          data-surface="commodity_primary"
          data-section="supply"
          data-article-title="고온에도 강한 쪽파 신품종 개발…출하 안정 기대"
          data-article-id="green-onion-variety"
          data-target-domain="example.com"
          data-item-key="green_onion"
          data-item-label="대파"
          data-representative-rank="3"
          data-representative-score="125.0"
          data-board-score="95.0"
          data-selection-fit="1.6"
          data-selection-stage="core"
          href="https://example.com/green-onion-variety"
        >대표</a>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-06-11T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "고온에도 강한 쪽파 신품종 개발…출하 안정 기대",
                        "link": "https://example.com/green-onion-variety",
                        "description": "쪽파 신품종 개발로 고온기 출하 안정이 기대된다는 기사다.",
                        "selection_fit_score": 1.6,
                        "selection_stage": "core",
                        "score": 80.0,
                        "pub_dt_kst": "2026-06-11T05:00:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-06-11", html, snapshot_payload)

        self.assertEqual(result["metrics"]["commodity_primary_strict_link_rate"], 1.0)
        self.assertEqual(result["metrics"]["commodity_primary_false_link_rate"], 0.0)
        self.assertEqual(result["commodity_primary_linkage_samples"], [])

    def test_commodity_board_daily_min_prevents_false_low_coverage_feedback(self) -> None:
        rows = [
            ("onion", "양파", "supply", "양파 가격 하락에 수급 안정 대책 착수"),
            ("napa_cabbage", "배추", "supply", "폭염 변수에 배추 수급 관리 비상"),
            ("garlic", "마늘", "dist", "마늘 가격 약세에 산지 출하 조절 확대"),
            ("green_onion", "대파", "policy", "대파 가격 하락 대응 수급 안정 점검"),
            ("potato", "감자", "supply", "감자 가격 약세로 산지 작황 희비"),
            ("lettuce", "상추", "dist", "상추값 다시 상승…도매시장 반입 감소"),
        ]
        html = "\n".join(
            f"""
            <a
              data-surface="commodity_primary"
              data-section="{section}"
              data-article-title="{title}"
              data-article-id="{key}"
              data-target-domain="example.com"
              data-item-key="{key}"
              data-item-label="{label}"
              data-representative-rank="3"
              data-representative-score="125.0"
              data-board-score="95.0"
              data-selection-fit="1.6"
              data-selection-stage="core"
              href="https://example.com/{key}"
            >대표</a>
            """
            for key, label, section, title in rows
        )
        raw_by_section = {section: [] for section in report_eval.SECTION_KEYS}
        for key, _label, section, title in rows:
            raw_by_section[section].append(
                {
                    "section": section,
                    "title": title,
                    "link": f"https://example.com/{key}",
                    "description": f"{title} 관련 현장 기사다.",
                    "selection_fit_score": 1.6,
                    "selection_stage": "core",
                    "score": 80.0,
                    "pub_dt_kst": "2026-06-11T05:00:00+09:00",
                }
            )
        snapshot_payload = {
            "window": {"end_kst": "2026-06-11T06:00:00+09:00"},
            "raw_by_section": raw_by_section,
        }

        result = report_eval.evaluate_report("2026-06-11", html, snapshot_payload)

        self.assertEqual(result["metrics"]["commodity_primary_count"], 6)
        self.assertFalse(result["metrics"]["commodity_board_low_coverage"])
        self.assertNotIn(
            "commodity_board_low_coverage",
            result["selection_guardrails"]["driver_tags"],
        )
        self.assertFalse(
            any("coverage" in hint for hint in result["improvement_hints"]),
            result["improvement_hints"],
        )

    def test_evaluate_report_does_not_flag_broadcast_report_as_finance_noise(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="supply"
          data-article-title="[D리포트] 중국산 사과 묘목 밀수 일당 16명 적발…63만 주 압수"
          data-href="https://news.sbs.co.kr/news/endPage.do?news_id=N1008539140"
          data-article-id="sbs-seedling"
          data-target-domain="news.sbs.co.kr"
          data-selection-fit="2.2"
          data-selection-stage="core"
          data-is-core="1"
        >
          <span class="badgeCore">핵심</span>
          <div class="sum">사과 묘목 밀수와 과수화상병 검역 위험을 전했다.</div>
        </div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-04-30T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "[D리포트] 중국산 사과 묘목 밀수 일당 16명 적발…63만 주 압수",
                        "link": "https://news.sbs.co.kr/news/endPage.do?news_id=N1008539140",
                        "description": "중국산 사과 묘목과 복숭아 묘목을 밀수한 일당이 적발됐고 검역본부가 과수화상병 유입 위험을 설명했다.",
                        "selection_fit_score": 0.0,
                        "selection_stage": "",
                        "score": 88.0,
                        "pub_dt_kst": "2026-04-30T05:00:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-04-30", html, snapshot_payload)

        self.assertEqual(result["metrics"]["content_false_positive_rate"], 0.0)
        self.assertEqual(result["content_false_positive_samples"], [])
        self.assertGreater(result["scores"]["core_quality"], 80.0)

    def test_quantified_public_distribution_execution_is_not_event_filler(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="dist"
          data-article-title="aT, 유통 본부 회의 개최…공공급식 거래액 2.3%↑·스마트 APC 115개 확대"
          data-href="https://example.com/at-public-distribution"
          data-article-id="at-public-distribution"
          data-target-domain="example.com"
          data-selection-fit="3.7"
          data-selection-stage="dist_publish_daily_floor_replacement"
          data-is-core="0"
        >
          <div class="sum">aT가 공공급식플랫폼 거래액 증가와 스마트 APC 확대 실적을 점검했다.</div>
        </div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-07-01T06:00:00+09:00"},
            "raw_by_section": {
                "dist": [
                    {
                        "section": "dist",
                        "title": "aT, 유통 본부 회의 개최…공공급식 거래액 2.3%↑·스마트 APC 115개 확대",
                        "link": "https://example.com/at-public-distribution",
                        "description": (
                            "aT가 생산유통통합조직과 공공급식플랫폼 거래액 2.3% 증가, "
                            "스마트 APC 115개소 확대 실적을 발표했다."
                        ),
                        "selection_fit_score": 3.7,
                        "selection_stage": "dist_publish_daily_floor_replacement",
                        "score": 60.0,
                        "pub_dt_kst": "2026-07-01T05:00:00+09:00",
                    }
                ],
                "supply": [],
                "policy": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-07-01", html, snapshot_payload)

        self.assertEqual(result["metrics"]["promotional_filler_rate"], 0.0)
        self.assertEqual(result["metrics"]["dist_weak_ops_rate"], 0.0)
        self.assertEqual(result["editorial_quality_samples"], [])

    def test_priority_locust_outbreak_core_overrides_stale_pool_rank(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="pest"
          data-article-title="'풀무치 떼의 습격'…고흥만 간척지 비상"
          data-href="https://example.com/locust-outbreak"
          data-article-id="locust-outbreak"
          data-target-domain="example.com"
          data-selection-fit="3.19"
          data-selection-stage="pest_publish_editorial_core"
          data-is-core="1"
        >
          <span class="badgeCore">핵심</span>
          <div class="sum">풀무치가 집단 발생해 농정 당국이 긴급 방제에 나섰다.</div>
        </div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-06-30T06:00:00+09:00"},
            "raw_by_section": {
                "pest": [
                    {
                        "section": "pest",
                        "title": "'풀무치 떼의 습격'…고흥만 간척지 비상",
                        "link": "https://example.com/locust-outbreak",
                        "description": "풀무치가 집단 발생해 벼와 조사료 재배지로 번지자 농정 당국이 긴급 방제에 나섰다.",
                        "selection_fit_score": 3.19,
                        "selection_stage": "pest_publish_editorial_core",
                        "score": 7.76,
                        "pub_dt_kst": "2026-06-29T18:00:00+09:00",
                    },
                    {
                        "section": "pest",
                        "title": "병해충 일반 안내",
                        "link": "https://example.com/high-rank-pest",
                        "description": "병해충 예찰 안내다.",
                        "selection_fit_score": 3.5,
                        "selection_stage": "core_final",
                        "score": 90.0,
                        "pub_dt_kst": "2026-06-29T17:00:00+09:00",
                    },
                ],
                "supply": [],
                "policy": [],
                "dist": [],
            },
        }

        result = report_eval.evaluate_report("2026-06-30", html, snapshot_payload)

        self.assertEqual(result["metrics"]["weak_core_rate"], 0.0)
        self.assertEqual(result["metrics"]["core_rank_percentile_avg"], 1.0)

    def test_authoritative_warning_and_live_prediction_are_priority_pest_cores(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="pest"
          data-article-title="경북농기원, 장마철 고추 탄저병 주의 당부"
          data-href="https://example.com/pepper-warning"
          data-article-id="pepper-warning"
          data-target-domain="example.com"
          data-selection-fit="2.89"
          data-selection-stage="pest_publish_editorial_core"
          data-is-core="1"
        ><div class="sum">농기원이 고추 탄저병 확산을 경고하고 비 전 살균제 방제를 당부했다.</div></div>
        <div
          data-surface="briefing_card"
          data-section="pest"
          data-article-title="경기도농업기술원, 병해충 위험 AI 조기 예측"
          data-href="https://example.com/pest-ai-warning"
          data-article-id="pest-ai-warning"
          data-target-domain="example.com"
          data-selection-fit="3.55"
          data-selection-stage="pest_publish_editorial_core"
          data-is-core="1"
        ><div class="sum">벼·콩 병해충 위험을 AI로 분석해 예보부터 경보까지 실시간 제공한다.</div></div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-07-01T06:00:00+09:00"},
            "raw_by_section": {
                "pest": [
                    {
                        "section": "pest",
                        "title": "경북농기원, 장마철 고추 탄저병 주의 당부",
                        "link": "https://example.com/pepper-warning",
                        "description": (
                            "경북농업기술원이 고추 탄저병 확산을 경고하고 비 전 살균제 살포와 "
                            "비 뒤 피해 과실 제거, 치료 약제 방제를 당부했다."
                        ),
                        "selection_fit_score": 2.89,
                        "selection_stage": "pest_publish_editorial_core",
                        "score": 20.0,
                        "pub_dt_kst": "2026-07-01T05:00:00+09:00",
                    },
                    {
                        "section": "pest",
                        "title": "경기도농업기술원, 병해충 위험 AI 조기 예측",
                        "link": "https://example.com/pest-ai-warning",
                        "description": (
                            "경기도농업기술원이 벼와 콩 등 농작물 병해충 위험도를 분석해 "
                            "예보·주의보·경보를 실시간 제공한다."
                        ),
                        "selection_fit_score": 3.55,
                        "selection_stage": "pest_publish_editorial_core",
                        "score": 21.0,
                        "pub_dt_kst": "2026-07-01T04:00:00+09:00",
                    },
                    {
                        "section": "pest",
                        "title": "일반 병해충 지원 소식",
                        "link": "https://example.com/high-score-generic",
                        "description": "지역 농가에 방제장비를 지원했다.",
                        "selection_fit_score": 3.8,
                        "selection_stage": "core_final",
                        "score": 90.0,
                        "pub_dt_kst": "2026-07-01T03:00:00+09:00",
                    },
                ],
                "supply": [],
                "policy": [],
                "dist": [],
            },
        }

        result = report_eval.evaluate_report("2026-07-01", html, snapshot_payload)

        self.assertEqual(result["metrics"]["weak_core_rate"], 0.0)
        self.assertEqual(result["metrics"]["core_rank_percentile_avg"], 1.0)

    def test_commodity_item_focus_uses_snapshot_body_context(self) -> None:
        html = """
        <a
          data-surface="commodity_primary"
          data-section="supply"
          data-article-title="도매시장 반입 줄어 가격 상승"
          data-article-id="commodity-apple"
          data-target-domain="example.com"
          data-item-key="apple"
          data-item-label="사과"
          data-representative-rank="3"
          data-selection-fit="1.4"
          data-selection-stage="core_final"
          href="https://example.com/apple-market"
        >대표기사</a>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-04-24T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "도매시장 반입 줄어 가격 상승",
                        "link": "https://example.com/apple-market",
                        "description": "사과 산지 출하가 줄고 도매시장 반입량이 감소하면서 경락가 상승세가 이어졌다.",
                        "selection_fit_score": 1.4,
                        "selection_stage": "core_final",
                        "score": 88.0,
                        "pub_dt_kst": "2026-04-24T05:00:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-04-24", html, snapshot_payload)

        self.assertEqual(result["metrics"]["commodity_primary_item_focus_rate"], 1.0)

    def test_monday_freshness_weights_weekend_collection_span(self) -> None:
        summary = "사과 산지 출하량과 도매시장 반입 흐름을 점검하고 가격 변동 가능성을 설명했다. 농가와 유통 주체의 대응 방향도 함께 전했다."
        html = "\n".join(
            f"""
            <div
              data-surface="briefing_card"
              data-section="supply"
              data-article-title="사과 주말 출하 점검 {idx}"
              data-href="https://example.com/apple-{idx}"
              data-article-id="brief-{idx}"
              data-target-domain="example.com"
            >
              <div class="sum">{summary}</div>
            </div>
            """
            for idx in range(4)
        )
        raw_items = [
            {
                "section": "supply",
                "title": f"사과 주말 출하 점검 {idx}",
                "link": f"https://example.com/apple-{idx}",
                "description": "사과 산지 출하량과 도매시장 반입 흐름을 점검했다.",
                "selection_fit_score": 1.4,
                "selection_stage": "core_final",
                "score": 85.0,
                "pub_dt_kst": f"2026-04-17T{idx + 8:02d}:00:00+09:00",
            }
            for idx in range(4)
        ]
        snapshot_payload = {
            "window": {
                "start_kst": "2026-04-17T06:00:00+09:00",
                "end_kst": "2026-04-20T06:00:00+09:00",
            },
            "raw_by_section": {"supply": raw_items, "policy": [], "dist": [], "pest": []},
        }

        monday = report_eval.evaluate_report("2026-04-20", html, snapshot_payload)
        regular = report_eval.evaluate_report("2026-04-21", html, {**snapshot_payload, "window": {"end_kst": "2026-04-21T06:00:00+09:00"}})

        self.assertEqual(monday["metrics"]["freshness_window_mode"], "weekend_span")
        self.assertGreater(monday["scores"]["freshness"], regular["scores"]["freshness"])
        self.assertGreaterEqual(monday["scores"]["freshness"], 85.0)

    def test_eval_flags_foreign_unmanaged_commodity(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="policy"
          data-article-title="한국향 두리안 수출 262% 급증에도...울상짓는 베트남 농가?"
          data-href="https://www.ajunews.com/view/20260518142237838"
          data-article-id="durian"
          data-target-domain="www.ajunews.com"
          data-selection-fit="5.1"
          data-selection-stage="tail"
        >
          <div class="sum">베트남 두리안 수출은 1분기 전년 대비 230% 늘었다.</div>
        </div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-05-19T06:00:00+09:00"},
            "raw_by_section": {
                "policy": [
                    {
                        "section": "policy",
                        "title": "한국향 두리안 수출 262% 급증에도...울상짓는 베트남 농가?",
                        "link": "https://www.ajunews.com/view/20260518142237838",
                        "description": "베트남 두리안 수출과 현지 농가 불안을 다룬 기사다.",
                        "selection_fit_score": 5.1,
                        "selection_stage": "tail",
                        "score": 80.0,
                        "pub_dt_kst": "2026-05-18T14:22:00+09:00",
                    }
                ],
                "supply": [],
                "dist": [],
                "pest": [],
            },
        }
        result = report_eval.evaluate_report("2026-05-19", html, snapshot_payload)
        self.assertEqual(result["metrics"]["off_scope_foreign_rate"], 1.0)
        self.assertEqual(result["content_false_positive_samples"][0]["reason"], "foreign_unmanaged_commodity")

    def test_eval_keeps_authoritative_domestic_multi_price_bulletin(self) -> None:
        html = """
        <div
          data-surface="briefing_card"
          data-section="supply"
          data-article-title="늦어지는 장마·무더위에 농산물값, 체리·파프리카↓, 다다기오이↑"
          data-href="https://www.ytn.co.kr/_ln/0102_202606291118044521"
          data-article-id="at-market"
          data-target-domain="ytn.co.kr"
          data-selection-fit="7.0"
          data-selection-stage="core_final"
        >
          <div class="sum">aT는 파프리카·감자 가격 하락과 오이·참외 가격 상승을 발표했다.</div>
        </div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-06-30T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "늦어지는 장마·무더위에 농산물값, 체리·파프리카↓, 다다기오이↑",
                        "link": "https://www.ytn.co.kr/_ln/0102_202606291118044521",
                        "description": (
                            "한국농수산식품유통공사는 파프리카 가격이 전주 대비 17.1% 하락하고 "
                            "감자 생산량 증가로 13.4% 내렸다고 밝혔다. 미국 체리와 망고도 다뤘지만 "
                            "다다기오이는 반입량 감소로 3.2% 상승했고 참외 출하량도 늘었다."
                        ),
                        "selection_fit_score": 7.0,
                        "selection_stage": "core_final",
                        "score": 80.0,
                        "pub_dt_kst": "2026-06-29T11:18:00+09:00",
                    }
                ],
                "policy": [],
                "dist": [],
                "pest": [],
            },
        }

        result = report_eval.evaluate_report("2026-06-30", html, snapshot_payload)

        self.assertEqual(result["metrics"]["off_scope_foreign_rate"], 0.0)
        self.assertEqual(result["content_false_positive_samples"], [])

    def test_eval_flags_cross_section_same_event_duplicate(self) -> None:
        html = """
        <div data-surface="briefing_card" data-section="supply"
          data-article-title="평창군, 908개 농가에 농산물 가격안정 기금 21억 지원"
          data-href="https://www.yna.co.kr/view/AKR20260518061200062?input=1195m"
          data-article-id="pyeongchang-a" data-target-domain="www.yna.co.kr"
          data-selection-fit="2.3" data-selection-stage="tail"><div class="sum">평창군은 908개 농가에 가격안정 기금 21억을 지원한다.</div></div>
        <div data-surface="briefing_card" data-section="policy"
          data-article-title="평창군, 농축산물 가격 안정 기금 21억 지원 …908농가 '숨통'"
          data-href="http://www.enewstoday.co.kr/news/articleView.html?idxno=2430514"
          data-article-id="pyeongchang-b" data-target-domain="www.enewstoday.co.kr"
          data-selection-fit="5.2" data-selection-stage="tail"><div class="sum">평창군이 908농가에 21억 규모 가격 안정 기금을 지원했다.</div></div>
        """
        snapshot_payload = {
            "window": {"end_kst": "2026-05-19T06:00:00+09:00"},
            "raw_by_section": {
                "supply": [
                    {
                        "section": "supply",
                        "title": "평창군, 908개 농가에 농산물 가격안정 기금 21억 지원",
                        "link": "https://www.yna.co.kr/view/AKR20260518061200062?input=1195m",
                        "description": "평창군은 908개 농가에 가격안정 기금 21억을 지원한다.",
                        "selection_fit_score": 2.3,
                        "selection_stage": "tail",
                        "score": 70.0,
                        "pub_dt_kst": "2026-05-18T12:00:00+09:00",
                    }
                ],
                "policy": [
                    {
                        "section": "policy",
                        "title": "평창군, 농축산물 가격 안정 기금 21억 지원 …908농가 '숨통'",
                        "link": "http://www.enewstoday.co.kr/news/articleView.html?idxno=2430514",
                        "description": "평창군이 908농가에 21억 규모 가격 안정 기금을 지원했다.",
                        "selection_fit_score": 5.2,
                        "selection_stage": "tail",
                        "score": 80.0,
                        "pub_dt_kst": "2026-05-18T16:38:00+09:00",
                    }
                ],
                "dist": [],
                "pest": [],
            },
        }
        result = report_eval.evaluate_report("2026-05-19", html, snapshot_payload)
        self.assertEqual(result["metrics"]["story_duplicate_rate"], 0.5)
        self.assertIn(result["story_duplicate_samples"][0]["reason"], {"known_duplicate_url", "same_event_numbers"})

    def test_eval_scores_editorial_selection_risks(self) -> None:
        articles = [
            ("policy", "5월 입하 이후, 품종 교체 및 주산지 변동으로 일부 농산물 가격 오름세", "https://example.com/policy-price", True, "core"),
            ("supply", "NH농협 창녕군지부, 마늘 망 지원… 농업인 영농비 절감 기대", "https://example.com/garlic-support", True, "core"),
            ("dist", "강원 농협 연합판매사업 협의회, 2026 산지 유통 현장투어 개최", "https://example.com/dist-tour", True, "core"),
            ("dist", "블루베리 소득작목 육성 온힘", "https://example.com/blueberry-dev", False, "tail"),
            ("pest", "예측보다 빨랐다…과수화상병 충주·원주서 잇따라 발생", "https://example.com/fire-1", True, "core"),
            ("pest", "과수화상병 주의보", "https://example.com/fire-2", True, "core"),
            ("pest", "충북 충주 과수원서 과수화상병 올 첫 발생", "https://example.com/fire-3", False, "tail"),
        ]
        html = "\n".join(
            self._briefing_card(section, title, href, core=core, stage=stage)
            for section, title, href, core, stage in articles
        )
        raw_by_section = {section: [] for section in report_eval.SECTION_KEYS}
        for section, title, href, _core, stage in articles:
            raw_by_section[section].append(
                {
                    "section": section,
                    "title": title,
                    "link": href,
                    "description": title,
                    "selection_fit_score": 1.6,
                    "selection_stage": stage,
                    "score": 88.0,
                    "pub_dt_kst": "2026-05-20T05:00:00+09:00",
                }
            )
        result = report_eval.evaluate_report(
            "2026-05-20",
            html,
            {"window": {"end_kst": "2026-05-20T06:00:00+09:00"}, "raw_by_section": raw_by_section},
        )

        metrics = result["metrics"]
        self.assertGreater(metrics["policy_wrong_section_rate"], 0.0)
        self.assertGreater(metrics["promotional_filler_rate"], 0.0)
        self.assertGreater(metrics["promotional_core_rate"], 0.0)
        self.assertGreater(metrics["dist_weak_ops_rate"], 0.0)
        self.assertGreater(metrics["pest_theme_duplicate_rate"], 0.0)
        self.assertGreater(metrics["weak_core_editorial_rate"], 0.0)
        self.assertGreater(metrics["editorial_quality_penalty"], 0.0)
        self.assertTrue(result["editorial_quality_samples"])

    def test_eval_keeps_metric_pallet_logistics_core_clean(self) -> None:
        article = report_eval.SurfaceArticle(
            tag="div",
            surface=report_eval.BRIEFING_SURFACE,
            section="dist",
            title='"가락시장 물류 선진화 속도"…파렛트 운송지원 확대',
            href="http://www.amnews.co.kr/news/articleView.html?idxno=72651",
            article_id="pallet",
            domain="amnews.co.kr",
            summary="가락시장 파렛트 출하율과 운송비 지원 확대를 다룬 기사다.",
            is_core=True,
        )
        body = (
            "가락시장 농산물 물류체계 개선을 위해 파렛트 운송지원 사업을 확대한다. "
            "청과부류 전체 파렛트 출하율은 88%로 전년보다 5.3%포인트 증가했고 "
            "운송비 지원금은 파렛트 1장당 평균 5500원으로 확대된다."
        )

        self.assertEqual(report_eval._editorial_base_issue_reasons(article, body), [])

    def test_eval_keeps_quantified_policy_execution_clean(self) -> None:
        cases = (
            (
                "정부비축 국산 콩 6만5000톤 푼다",
                "정부가 가격 안정을 위해 비축 콩 6만5000톤을 시장에 공급한다.",
            ),
            (
                "물가 안정 위해 1조 원 투입",
                "정부가 농산물 물가 안정 대책에 1조 원을 투입해 시행한다.",
            ),
            (
                "수입 농산물 관리 효율화, 민·관 머리 맞댄다",
                "생산자와 소비자가 참여해 수입 농산물 관리 개선방안을 협의한다.",
            ),
        )
        for index, (title, body) in enumerate(cases):
            with self.subTest(title=title):
                article = report_eval.SurfaceArticle(
                    tag="div",
                    surface=report_eval.BRIEFING_SURFACE,
                    section="policy",
                    title=title,
                    href=f"https://example.com/policy-execution-{index}",
                    article_id=f"policy-execution-{index}",
                    domain="example.com",
                    summary=body,
                    is_core=index == 0,
                )
                self.assertEqual(report_eval._editorial_base_issue_reasons(article, body), [])

    def test_eval_keeps_direct_platform_and_measured_export_clean(self) -> None:
        cases = (
            (
                "제주 농특산물 직거래 플랫폼 '탐나는장터' 7월 10일 공식 오픈",
                "생산자는 판매 수수료와 마케팅 비용 부담을 줄이고 소비자에게 직접 판매한다. 공식 오픈한다.",
            ),
            (
                "K-참외 매력에 ‘흠뻑’…국산 참외 일본 수출 ‘쑥쑥’",
                "국산 참외의 일본 수출량과 현지 판매량이 해마다 증가하고 있다.",
            ),
        )
        for index, (title, body) in enumerate(cases):
            with self.subTest(title=title):
                article = report_eval.SurfaceArticle(
                    tag="div",
                    surface=report_eval.BRIEFING_SURFACE,
                    section="dist",
                    title=title,
                    href=f"https://example.com/dist-channel-{index}",
                    article_id=f"dist-channel-{index}",
                    domain="example.com",
                    summary=body,
                    is_core=False,
                )
                self.assertEqual(report_eval._editorial_base_issue_reasons(article, body), [])

    def test_markdown_and_history_renderers_have_expected_shape(self) -> None:
        result = report_eval.evaluate_report(self.report_date, self.html_text, self.snapshot_payload)
        result["operational_score"] = result["overall_score"]
        result["editorial_score"] = 91.0
        result["editorial"] = {
            "status": "success",
            "model": "gpt-5.5",
            "model_snapshot": "gpt-5.5-2026-04-23",
            "score": 91.0,
            "target_score": 95.0,
            "target_status": "needs_minor_iteration",
            "scores": {
                "article_selection": 91.0,
                "section_fit": 92.0,
                "core_pick_quality": 90.0,
                "summary_usefulness": 93.0,
                "missed_opportunity": 88.0,
                "noise_control": 94.0,
            },
            "summary": "Good but not perfect.",
            "issues": [
                {"type": "missed_better_candidate", "severity": "medium", "title": "candidate", "reason": "better option visible"},
                {"type": "duplicate", "severity": "high", "title": "same issue", "reason": "same event repeated"},
            ],
        }
        markdown = report_eval.render_evaluation_markdown(result)
        history_entry = report_eval.result_to_history_entry(result)
        selection_feedback = report_eval.build_selection_feedback_payload(result)

        self.assertIn("## Daily Eval", markdown)
        self.assertIn(self.report_date, markdown)
        self.assertIn("section_fit=", markdown)
        self.assertIn("Editorial Shadow Eval", markdown)
        self.assertIn("Model: gpt-5.5 (resolved gpt-5.5-2026-04-23)", markdown)
        self.assertEqual(history_entry["report_date"], self.report_date)
        self.assertIn("overall_score", history_entry)
        self.assertEqual(history_entry["editorial_score"], 91.0)
        self.assertNotIn("editorial_duplicate_topic", selection_feedback["selection_guardrails"]["driver_tags"])
        self.assertEqual(selection_feedback["editorial_guardrail_mode"], "advisory_only")
        self.assertIn("editorial_duplicate_topic", selection_feedback["editorial_suggested_guardrails"]["driver_tags"])


if __name__ == "__main__":
    unittest.main()
