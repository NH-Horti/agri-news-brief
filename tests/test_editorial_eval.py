import json
import unittest
from pathlib import Path

import editorial_eval
import report_eval


ROOT = Path(__file__).resolve().parents[1]


class _FakeResponse:
    status_code = 200

    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class _FakeSession:
    def __init__(self):
        self.requests = []

    def post(self, url, headers=None, json=None, timeout=None):
        self.requests.append(
            {
                "url": url,
                "headers": headers or {},
                "json": json or {},
                "timeout": timeout,
            }
        )
        return _FakeResponse(
            {
                "output_text": json_module_dumps(
                    {
                        "score": 91,
                        "scores": {
                            "article_selection": 90,
                            "section_fit": 92,
                            "core_pick_quality": 89,
                            "summary_usefulness": 93,
                            "missed_opportunity": 88,
                            "noise_control": 94,
                        },
                        "summary": "Good briefing with a few visible selection misses.",
                        "issues": [
                            {
                                "type": "missed_better_candidate",
                                "severity": "medium",
                                "section": "supply",
                                "title": "Candidate title",
                                "reason": "A stronger raw candidate was available.",
                                "suggested_action": "Raise recall for the section.",
                            }
                        ],
                        "section_notes": {"supply": "Review top raw pool."},
                        "improvement_suggestions": ["Tighten core selection."],
                    }
                )
            }
        )


def json_module_dumps(payload):
    return json.dumps(payload)


class EditorialEvalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report_date = "2026-04-10"
        cls.html_text = (ROOT / "docs" / "archive" / f"{cls.report_date}.html").read_text(encoding="utf-8")
        cls.snapshot_payload = report_eval.load_snapshot_payload(
            ROOT / "docs" / "replay" / f"{cls.report_date}.snapshot.json"
        )
        cls.operational_result = report_eval.evaluate_report(cls.report_date, cls.html_text, cls.snapshot_payload)

    def test_build_editorial_payload_includes_selected_and_raw_candidates(self):
        payload = editorial_eval.build_editorial_payload(
            self.report_date,
            self.html_text,
            self.snapshot_payload,
            self.operational_result,
            max_raw_per_section=3,
        )

        self.assertEqual(payload["report_date"], self.report_date)
        self.assertGreater(len(payload["selected_briefing_cards"]), 0)
        self.assertEqual(len(payload["raw_candidates_by_section"]["supply"]), 3)
        self.assertIn("operational_eval", payload)

    def test_evaluate_editorial_quality_normalizes_llm_response(self):
        session = _FakeSession()
        result = editorial_eval.evaluate_editorial_quality(
            self.report_date,
            self.html_text,
            self.snapshot_payload,
            self.operational_result,
            api_key="test-key",
            model="test-model",
            max_raw_per_section=2,
            session_factory=lambda: session,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["score"], 91)
        self.assertEqual(result["scores"]["core_pick_quality"], 89)
        self.assertEqual(result["issues"][0]["type"], "missed_better_candidate")
        self.assertEqual(session.requests[0]["json"]["model"], "test-model")
        self.assertIn("raw_candidates_by_section", session.requests[0]["json"]["input"][1]["content"])

    def test_editorial_improvement_plan_maps_issues_to_shadow_actions(self):
        editorial_result = {
            "status": "success",
            "score": 91,
            "issues": [{"type": "missed_better_candidate"}, {"type": "noisy_article"}],
        }

        plan = editorial_eval.build_editorial_improvement_plan(editorial_result, self.operational_result)

        self.assertTrue(plan["proposal_only"])
        self.assertEqual(plan["target_status"], "needs_minor_iteration")
        action_kinds = {action["kind"] for action in plan["recommended_actions"]}
        self.assertIn("candidate_recall", action_kinds)
        self.assertIn("noise_filter", action_kinds)


if __name__ == "__main__":
    unittest.main()
