from __future__ import annotations

import sys
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


TEST_TARGETS = [
    "tests.test_regressions",
    "tests.test_report_eval",
    "tests.test_local_runtime",
    "tests.test_classifier_behavior.TestClassifierBehavior.test_dist_market_ops_context_matches_wholesale_logistics_automation_story",
    "tests.test_classifier_behavior.TestClassifierBehavior.test_dist_consumer_tail_context_keeps_wholesale_cost_support_story",
    "tests.test_classifier_behavior.TestClassifierBehavior.test_dist_market_ops_stories_with_different_signatures_are_not_merged",
    "tests.test_classifier_behavior.TestClassifierBehavior.test_dist_selection_keeps_distinct_market_ops_from_same_press",
    "tests.test_classifier_behavior.TestClassifierBehavior.test_dist_underfill_adds_online_wholesale_ops_story",
    "tests.test_classifier_behavior.TestClassifierBehavior.test_dist_selection_keeps_center_and_sales_channel_ops_stories",
]


def build_suite() -> unittest.TestSuite:
    loader = unittest.defaultTestLoader
    return loader.loadTestsFromNames(TEST_TARGETS)


def main() -> int:
    suite = build_suite()
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
