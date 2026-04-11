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

    def test_evaluate_report_returns_scores_and_feedback(self) -> None:
        result = report_eval.evaluate_report(self.report_date, self.html_text, self.snapshot_payload)

        self.assertEqual(result["counts"]["briefing_total"], 15)
        self.assertIn(result["status"], {"pass", "warn", "fail"})
        self.assertGreaterEqual(result["overall_score"], 0.0)
        self.assertLessEqual(result["overall_score"], 100.0)
        self.assertTrue(result["improvement_hints"])
        self.assertTrue(result["summary_prompt_feedback"])
        self.assertIn("summary_quality", result["scores"])

    def test_markdown_and_history_renderers_have_expected_shape(self) -> None:
        result = report_eval.evaluate_report(self.report_date, self.html_text, self.snapshot_payload)
        markdown = report_eval.render_evaluation_markdown(result)
        history_entry = report_eval.result_to_history_entry(result)

        self.assertIn("## Daily Eval", markdown)
        self.assertIn(self.report_date, markdown)
        self.assertEqual(history_entry["report_date"], self.report_date)
        self.assertIn("overall_score", history_entry)


if __name__ == "__main__":
    unittest.main()
