import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from orchestrator import OrchestratorContext, OrchestratorHandlers, execute_orchestration


class TestOrchestrator(unittest.TestCase):
    def _handlers(self, calls):
        return OrchestratorHandlers(
            run_ux_patch=lambda repo, end: calls.append(("ux_patch", repo)),
            run_maintenance_rebuild=lambda repo, end, task: calls.append((task, repo)),
            run_force_rebuild=lambda repo, end: calls.append(("force_rebuild", repo)),
            run_daily=lambda repo, end, task: calls.append(("daily", repo)),
            is_business_day=lambda _end: True,
            on_skip_non_business=lambda _end: calls.append(("skip_non_business", "")),
        )

    def test_dispatches_ux_patch(self):
        calls = []
        ctx = OrchestratorContext(
            repo="org/repo",
            end_kst=datetime.now(timezone.utc),
            maintenance_task="ux_patch",
            force_report_date="",
            force_run_anyday=False,
            naver_ready=True,
            kakao_ready=True,
        )
        execute_orchestration(ctx, self._handlers(calls))
        self.assertEqual(calls, [("ux_patch", "org/repo")])

    def test_dispatches_daily_when_ready(self):
        calls = []
        ctx = OrchestratorContext(
            repo="org/repo",
            end_kst=datetime.now(timezone.utc),
            maintenance_task="",
            force_report_date="",
            force_run_anyday=False,
            naver_ready=True,
            kakao_ready=True,
        )
        execute_orchestration(ctx, self._handlers(calls))
        self.assertEqual(calls, [("daily", "org/repo")])

    def test_skips_non_business_day(self):
        calls = []
        handlers = OrchestratorHandlers(
            run_ux_patch=lambda *_: calls.append(("ux_patch", "")),
            run_maintenance_rebuild=lambda *_: calls.append(("maintenance", "")),
            run_force_rebuild=lambda *_: calls.append(("force_rebuild", "")),
            run_daily=lambda *_: calls.append(("daily", "")),
            is_business_day=lambda _end: False,
            on_skip_non_business=lambda _end: calls.append(("skip_non_business", "")),
        )
        ctx = OrchestratorContext(
            repo="org/repo",
            end_kst=datetime.now(timezone.utc),
            maintenance_task="",
            force_report_date="",
            force_run_anyday=False,
            naver_ready=True,
            kakao_ready=True,
        )
        execute_orchestration(ctx, handlers)
        self.assertEqual(calls, [("skip_non_business", "")])

    def test_raises_when_naver_missing(self):
        calls = []
        ctx = OrchestratorContext(
            repo="org/repo",
            end_kst=datetime.now(timezone.utc),
            maintenance_task="",
            force_report_date="",
            force_run_anyday=False,
            naver_ready=False,
            kakao_ready=True,
        )
        with self.assertRaises(RuntimeError):
            execute_orchestration(ctx, self._handlers(calls))


if __name__ == "__main__":
    unittest.main()