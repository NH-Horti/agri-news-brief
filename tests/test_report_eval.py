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

    def test_editorial_quality_gate_caps_headline_score_below_target(self) -> None:
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

        self.assertEqual(result["overall_score"], 80.0)
        self.assertEqual(result["operational_score"], 98.13)
        self.assertEqual(result["status"], "warn")
        self.assertEqual(result["quality_gate"]["reason"], "editorial_below_target")
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
        self.assertEqual(result["commodity_primary_linkage_samples"][0]["item_label"], "애호박(쥬키니)")

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
        self.assertEqual(result["commodity_primary_linkage_samples"], [])

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

    def test_markdown_and_history_renderers_have_expected_shape(self) -> None:
        result = report_eval.evaluate_report(self.report_date, self.html_text, self.snapshot_payload)
        result["operational_score"] = result["overall_score"]
        result["editorial_score"] = 91.0
        result["editorial"] = {
            "status": "success",
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
        self.assertEqual(history_entry["report_date"], self.report_date)
        self.assertIn("overall_score", history_entry)
        self.assertEqual(history_entry["editorial_score"], 91.0)
        self.assertNotIn("editorial_duplicate_topic", selection_feedback["selection_guardrails"]["driver_tags"])
        self.assertEqual(selection_feedback["editorial_guardrail_mode"], "advisory_only")
        self.assertIn("editorial_duplicate_topic", selection_feedback["editorial_suggested_guardrails"]["driver_tags"])


if __name__ == "__main__":
    unittest.main()
