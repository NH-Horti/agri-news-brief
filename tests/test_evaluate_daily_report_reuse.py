import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts import evaluate_daily_report


ROOT = Path(__file__).resolve().parents[1]


class EvaluateDailyReportReuseTests(unittest.TestCase):
    def test_existing_result_reuse_does_not_repeat_evaluators(self):
        report_date = "2026-04-10"
        snapshot = ROOT / "docs" / "replay" / f"{report_date}.snapshot.json"
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            existing = output_root / "existing.json"
            existing.write_text(
                json.dumps(
                    {
                        "report_date": report_date,
                        "generated_at_kst": "2026-04-10T06:20:00+09:00",
                        "overall_score": 91.0,
                        "operational_score": 98.0,
                        "status": "pass",
                        "counts": {},
                        "metrics": {},
                        "scores": {},
                        "editorial": {"status": "success", "score": 91.0},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            argv = [
                "evaluate_daily_report.py",
                "--report-date",
                report_date,
                "--snapshot-path",
                str(snapshot),
                "--existing-result-json",
                str(existing),
                "--output-json",
                str(output_root / "result.json"),
                "--output-md",
                str(output_root / "result.md"),
                "--feedback-out",
                str(output_root / "feedback.txt"),
                "--selection-feedback-out",
                str(output_root / "selection.json"),
                "--fail-under",
                "88",
            ]
            with (
                patch.object(sys, "argv", argv),
                patch.object(evaluate_daily_report, "evaluate_report", side_effect=AssertionError("must not run")),
                patch.object(
                    evaluate_daily_report,
                    "evaluate_editorial_quality",
                    side_effect=AssertionError("must not run"),
                ),
            ):
                exit_code = evaluate_daily_report.main()

            self.assertEqual(exit_code, 0)
            saved = json.loads((output_root / "result.json").read_text(encoding="utf-8"))
            self.assertEqual(saved["overall_score"], 91.0)


if __name__ == "__main__":
    unittest.main()
