import unittest
from datetime import datetime, timezone

from scripts.delivery_watchdog_decision import decide_delivery_action


class DeliveryWatchdogDecisionTests(unittest.TestCase):
    def _run(
        self,
        run_id: int,
        created_at: str,
        *,
        status: str = "completed",
        conclusion: str = "failure",
        title: str = "daily trigger=cloudflare-cron recovery=false",
    ) -> dict:
        return {
            "id": run_id,
            "created_at": created_at,
            "status": status,
            "conclusion": conclusion,
            "display_title": title,
            "html_url": f"https://example.test/runs/{run_id}",
        }

    def test_success_receipt_records_on_time_delivery(self):
        decision = decide_delivery_action(
            {"status": "success", "sent_at_kst": "2026-08-03T06:24:00+09:00"},
            {"workflow_runs": []},
            now=datetime(2026, 8, 2, 22, 0, tzinfo=timezone.utc),
            report_date="2026-08-03",
        )

        self.assertEqual(decision["result"], "delivery-confirmed-on-time")
        self.assertTrue(decision["delivery_on_time"])
        self.assertEqual(decision["action"], "none")

    def test_late_receipt_is_visible_as_sla_failure(self):
        decision = decide_delivery_action(
            {"status": "success", "sent_at_kst": "2026-08-03T07:01:00+09:00"},
            {"workflow_runs": []},
            now=datetime(2026, 8, 2, 22, 2, tzinfo=timezone.utc),
            report_date="2026-08-03",
        )

        self.assertEqual(decision["result"], "delivery-confirmed-late")
        self.assertFalse(decision["delivery_on_time"])

    def test_completed_failure_dispatches_forced_recovery(self):
        decision = decide_delivery_action(
            {},
            {"workflow_runs": [self._run(10, "2026-08-02T21:05:00Z")]},
            now=datetime(2026, 8, 2, 21, 20, tzinfo=timezone.utc),
            report_date="2026-08-03",
        )

        self.assertEqual(decision["action"], "dispatch")
        self.assertEqual(decision["result"], "delivery-missing")

    def test_early_active_run_is_allowed_to_finish(self):
        decision = decide_delivery_action(
            {},
            {
                "workflow_runs": [
                    self._run(11, "2026-08-02T20:35:00Z", status="in_progress", conclusion="")
                ]
            },
            now=datetime(2026, 8, 2, 20, 50, tzinfo=timezone.utc),
            report_date="2026-08-03",
        )

        self.assertEqual(decision["action"], "wait")
        self.assertEqual(decision["run_age_minutes"], 15)

    def test_stale_run_is_cancelled_after_recovery_cutoff(self):
        decision = decide_delivery_action(
            {},
            {
                "workflow_runs": [
                    self._run(12, "2026-08-02T21:05:00Z", status="in_progress", conclusion="")
                ]
            },
            now=datetime(2026, 8, 2, 21, 35, tzinfo=timezone.utc),
            report_date="2026-08-03",
        )

        self.assertEqual(decision["action"], "cancel_and_dispatch")
        self.assertEqual(decision["run_age_minutes"], 30)

    def test_hard_cutoff_cancels_a_recent_but_unlikely_to_finish_run(self):
        decision = decide_delivery_action(
            {},
            {
                "workflow_runs": [
                    self._run(13, "2026-08-02T21:30:00Z", status="in_progress", conclusion="")
                ]
            },
            now=datetime(2026, 8, 2, 21, 40, tzinfo=timezone.utc),
            report_date="2026-08-03",
        )

        self.assertEqual(decision["action"], "cancel_and_dispatch")

    def test_failed_primary_preempts_a_new_primary_after_recovery_cutoff(self):
        decision = decide_delivery_action(
            {},
            {
                "workflow_runs": [
                    self._run(14, "2026-08-02T21:05:00Z"),
                    self._run(
                        15,
                        "2026-08-02T21:27:00Z",
                        status="in_progress",
                        conclusion="",
                        title="daily trigger=github-schedule recovery=false",
                    ),
                ]
            },
            now=datetime(2026, 8, 2, 21, 31, tzinfo=timezone.utc),
            report_date="2026-08-03",
        )

        self.assertEqual(decision["action"], "cancel_and_dispatch")
        self.assertEqual(decision["result"], "failed-primary-with-active-replacement")
        self.assertEqual(decision["run_id"], "15")
        self.assertEqual(decision["run_age_minutes"], 4)
        self.assertEqual(decision["failed_primary_run_count"], 1)

    def test_failed_primary_does_not_preempt_before_recovery_cutoff(self):
        decision = decide_delivery_action(
            {},
            {
                "workflow_runs": [
                    self._run(16, "2026-08-02T21:05:00Z"),
                    self._run(
                        17,
                        "2026-08-02T21:27:00Z",
                        status="in_progress",
                        conclusion="",
                        title="daily trigger=github-schedule recovery=false",
                    ),
                ]
            },
            now=datetime(2026, 8, 2, 21, 29, tzinfo=timezone.utc),
            report_date="2026-08-03",
        )

        self.assertEqual(decision["action"], "wait")
        self.assertEqual(decision["result"], "daily-run-active")

    def test_failed_primary_does_not_preempt_an_active_recovery(self):
        decision = decide_delivery_action(
            {},
            {
                "workflow_runs": [
                    self._run(18, "2026-08-02T21:05:00Z"),
                    self._run(
                        19,
                        "2026-08-02T21:27:00Z",
                        status="in_progress",
                        conclusion="",
                        title="daily trigger=github-watchdog recovery=true",
                    ),
                ]
            },
            now=datetime(2026, 8, 2, 21, 31, tzinfo=timezone.utc),
            report_date="2026-08-03",
        )

        self.assertEqual(decision["action"], "wait")
        self.assertEqual(decision["result"], "daily-run-active")

    def test_recovery_limit_stops_dispatch_loop(self):
        runs = [
            self._run(
                index,
                f"2026-08-02T21:{20 + index:02d}:00Z",
                title="daily trigger=github-watchdog recovery=true",
            )
            for index in (1, 2)
        ]
        decision = decide_delivery_action(
            {},
            {"workflow_runs": runs},
            now=datetime(2026, 8, 2, 22, 0, tzinfo=timezone.utc),
            report_date="2026-08-03",
        )

        self.assertEqual(decision["result"], "recovery-attempt-limit-reached")
        self.assertEqual(decision["action"], "none")


if __name__ == "__main__":
    unittest.main()
