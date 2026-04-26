import unittest
from pathlib import Path

import report_eval


ROOT = Path(__file__).resolve().parents[1]


class ReportEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report_date = "2026-04-10"
        cls.html_text = (ROOT / "docs" / "archive" / f"{cls.report_date}.html").read_text(encoding="utf-8")
        cls.snapshot_payload = report_eval.load_snapshot_payload(
            ROOT / "docs" / "replay" / f"{cls.report_date}.snapshot.json"
        )

    def test_parse_report_html_extracts_briefing_cards_and_summaries(self) -> None:
        articles = report_eval.parse_report_html(self.html_text)
        briefing = [article for article in articles if article.surface == report_eval.BRIEFING_SURFACE]
        commodity = [article for article in articles if article.surface in report_eval.COMMODITY_SURFACES]

        self.assertEqual(len(briefing), 15)
        self.assertGreater(len(commodity), 20)
        self.assertTrue(any(article.is_core for article in briefing))
        self.assertTrue(all(article.summary.strip() for article in briefing))

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

    def test_markdown_and_history_renderers_have_expected_shape(self) -> None:
        result = report_eval.evaluate_report(self.report_date, self.html_text, self.snapshot_payload)
        markdown = report_eval.render_evaluation_markdown(result)
        history_entry = report_eval.result_to_history_entry(result)

        self.assertIn("## Daily Eval", markdown)
        self.assertIn(self.report_date, markdown)
        self.assertIn("section_fit=", markdown)
        self.assertEqual(history_entry["report_date"], self.report_date)
        self.assertIn("overall_score", history_entry)


if __name__ == "__main__":
    unittest.main()
