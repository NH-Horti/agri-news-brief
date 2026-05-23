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

    def _operational_with_uniform_counts(self, count: int = 5, raw: int = 10) -> dict:
        payload = json.loads(json.dumps(self.operational_result))
        counts = payload.get("counts", {})
        counts["briefing_by_section"] = {section: count for section in report_eval.SECTION_KEYS}
        counts["expected_briefing_by_section"] = {
            section: min(report_eval.PREFERRED_BRIEFING_COUNT_PER_SECTION, raw)
            for section in report_eval.SECTION_KEYS
        }
        counts["raw_by_section"] = {section: raw for section in report_eval.SECTION_KEYS}
        payload["counts"] = counts
        payload["scores"] = {
            **payload.get("scores", {}),
            "commodity_board_quality": 100.0,
        }
        return payload

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
        self.assertIn("section_count_targets", payload)
        self.assertGreater(payload["section_count_targets"]["score"], 0.0)
        self.assertLessEqual(payload["section_count_targets"]["score"], 100.0)

    def test_evaluate_editorial_quality_normalizes_llm_response(self):
        session = _FakeSession()
        result = editorial_eval.evaluate_editorial_quality(
            self.report_date,
            self.html_text,
            self.snapshot_payload,
            self._operational_with_uniform_counts(),
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
        self.assertEqual(session.requests[0]["json"]["text"]["format"]["type"], "json_schema")
        self.assertIn("raw_candidates_by_section", session.requests[0]["json"]["input"][1]["content"])
        self.assertIn("section_count_targets", session.requests[0]["json"]["input"][1]["content"])

    def test_section_count_gate_caps_editorial_target_when_underfilled(self):
        class HighScoreSession(_FakeSession):
            def post(self, url, headers=None, json=None, timeout=None):
                self.requests.append({"url": url, "headers": headers or {}, "json": json or {}, "timeout": timeout})
                return _FakeResponse(
                    {
                        "output_text": json_module_dumps(
                            {
                                "score": 99,
                                "scores": {
                                    "article_selection": 99,
                                    "section_fit": 99,
                                    "core_pick_quality": 99,
                                    "summary_usefulness": 99,
                                    "missed_opportunity": 99,
                                    "noise_control": 99,
                                },
                                "summary": "Looks strong.",
                                "issues": [],
                                "section_notes": {"supply": "", "policy": "", "dist": "", "pest": ""},
                                "improvement_suggestions": [],
                            }
                        )
                    }
                )

        underfilled = self._operational_with_uniform_counts(count=5, raw=10)
        counts = json.loads(json.dumps(underfilled["counts"]))
        counts["briefing_by_section"]["dist"] = 2
        counts["expected_briefing_by_section"]["dist"] = 5
        counts["raw_by_section"]["dist"] = 10
        underfilled["counts"] = counts

        result = editorial_eval.evaluate_editorial_quality(
            self.report_date,
            self.html_text,
            self.snapshot_payload,
            underfilled,
            api_key="test-key",
            model="test-model",
            session_factory=HighScoreSession,
        )

        self.assertEqual(result["status"], "success")
        self.assertLess(result["score"], 95)
        self.assertEqual(result["target_status"], "needs_iteration")
        self.assertEqual(result["section_count_status"], "underfilled")
        self.assertIn("section_count_adjustment", result)

    def test_operational_gate_calibrates_llm_shadow_score_when_publish_gates_pass(self):
        class LowButDebatableSession(_FakeSession):
            def post(self, url, headers=None, json=None, timeout=None):
                self.requests.append({"url": url, "headers": headers or {}, "json": json or {}, "timeout": timeout})
                return _FakeResponse(
                    {
                        "output_text": json_module_dumps(
                            {
                                "score": 84,
                                "scores": {
                                    "article_selection": 84,
                                    "section_fit": 86,
                                    "core_pick_quality": 82,
                                    "summary_usefulness": 78,
                                    "missed_opportunity": 80,
                                    "noise_control": 88,
                                },
                                "summary": "Debatable misses, but no deterministic failure.",
                                "issues": [
                                    {
                                        "type": "weak_core",
                                        "severity": "high",
                                        "section": "dist",
                                        "title": "Debatable core",
                                        "reason": "Subjective preference.",
                                        "suggested_action": "Review manually.",
                                    }
                                ],
                                "section_notes": {"dist": "Debatable."},
                                "improvement_suggestions": ["Review edge cases."],
                            }
                        )
                    }
                )

        calibrated_operational = json.loads(json.dumps(self.operational_result))
        calibrated_operational["overall_score"] = 97.9
        calibrated_operational["scores"] = {
            **calibrated_operational.get("scores", {}),
            "section_fit": 100.0,
            "core": 100.0,
            "summary": 100.0,
            "commodity_board_quality": 100.0,
        }
        calibrated_operational["metrics"] = {
            **calibrated_operational.get("metrics", {}),
            "false_positive_rate": 0.0,
            "weak_core_rate": 0.0,
            "editorial_penalty": 0.0,
            "semantic_penalty": 0.0,
        }
        counts = calibrated_operational.get("counts", {})
        counts["briefing_by_section"] = {"supply": 5, "policy": 5, "dist": 5, "pest": 5}
        counts["expected_briefing_by_section"] = {"supply": 5, "policy": 5, "dist": 5, "pest": 5}
        counts["raw_by_section"] = {"supply": 10, "policy": 10, "dist": 10, "pest": 10}
        calibrated_operational["counts"] = counts

        result = editorial_eval.evaluate_editorial_quality(
            self.report_date,
            self.html_text,
            self.snapshot_payload,
            calibrated_operational,
            api_key="test-key",
            model="test-model",
            session_factory=LowButDebatableSession,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["llm_score"], 84)
        self.assertEqual(result["score"], 95)
        self.assertEqual(result["target_status"], "target_met")
        self.assertEqual(result["score_calibration"]["reason"], "deterministic_publish_gates_passed")
        self.assertTrue(result["score_calibration"]["gates"]["commodity_board_score_min"])

    def test_section_count_gate_prefers_five_but_accepts_four_soft_fallback(self):
        operational = self._operational_with_uniform_counts(count=4, raw=10)
        context = editorial_eval._section_count_context(operational)

        self.assertGreaterEqual(context["score"], 95.0)
        self.assertEqual(context["status"], "target_met")
        self.assertEqual(set(context["soft_fallback_sections"]), set(report_eval.SECTION_KEYS))

        operational = self._operational_with_uniform_counts(count=3, raw=10)
        context = editorial_eval._section_count_context(operational)

        self.assertLess(context["score"], 95.0)
        self.assertEqual(context["status"], "minimum_fallback")

    def test_low_commodity_board_blocks_shadow_calibration(self):
        class LowButDebatableSession(_FakeSession):
            def post(self, url, headers=None, json=None, timeout=None):
                self.requests.append({"url": url, "headers": headers or {}, "json": json or {}, "timeout": timeout})
                return _FakeResponse(
                    {
                        "output_text": json_module_dumps(
                            {
                                "score": 84,
                                "scores": {
                                    "article_selection": 84,
                                    "section_fit": 86,
                                    "core_pick_quality": 82,
                                    "summary_usefulness": 78,
                                    "missed_opportunity": 80,
                                    "noise_control": 88,
                                },
                                "summary": "Debatable misses, but no deterministic failure.",
                                "issues": [],
                                "section_notes": {"dist": "Debatable."},
                                "improvement_suggestions": ["Review edge cases."],
                            }
                        )
                    }
                )

        operational = self._operational_with_uniform_counts(count=5, raw=10)
        operational["overall_score"] = 97.9
        operational["scores"] = {
            **operational.get("scores", {}),
            "section_fit": 100.0,
            "core": 100.0,
            "summary": 100.0,
            "commodity_board_quality": 82.0,
        }
        operational["metrics"] = {
            **operational.get("metrics", {}),
            "false_positive_rate": 0.0,
            "weak_core_rate": 0.0,
            "editorial_penalty": 0.0,
            "semantic_penalty": 0.0,
        }

        result = editorial_eval.evaluate_editorial_quality(
            self.report_date,
            self.html_text,
            self.snapshot_payload,
            operational,
            api_key="test-key",
            model="test-model",
            session_factory=LowButDebatableSession,
        )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["score"], 84)
        self.assertNotIn("score_calibration", result)

    def test_editorial_improvement_plan_maps_issues_to_shadow_actions(self):
        editorial_result = {
            "status": "success",
            "score": 91,
            "issues": [{"type": "missed_better_candidate"}, {"type": "noisy_article"}],
        }

        plan = editorial_eval.build_editorial_improvement_plan(editorial_result, self.operational_result)

        self.assertTrue(plan["proposal_only"])
        self.assertEqual(plan["mode"], "shadow_replay_loop")
        self.assertEqual(plan["target_status"], "needs_minor_iteration")
        self.assertIn("promotion_gates", plan)
        action_kinds = {action["kind"] for action in plan["recommended_actions"]}
        self.assertIn("candidate_recall", action_kinds)
        self.assertIn("noise_filter", action_kinds)


if __name__ == "__main__":
    unittest.main()
