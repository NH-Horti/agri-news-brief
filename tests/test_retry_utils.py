import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime

from retry_utils import parse_retry_after, retry_after_or_backoff


class TestRetryUtils(unittest.TestCase):
    def test_parse_retry_after_handles_missing_and_invalid(self):
        self.assertEqual(parse_retry_after(None), 0.0)
        self.assertEqual(parse_retry_after({}), 0.0)
        self.assertEqual(parse_retry_after({"Retry-After": "abc"}), 0.0)

    def test_parse_retry_after_supports_http_date(self):
        future = datetime.now(timezone.utc) + timedelta(seconds=3)
        header = format_datetime(future)
        delay = parse_retry_after({"Retry-After": header})
        self.assertGreaterEqual(delay, 0.0)
        self.assertLessEqual(delay, 5.0)

    def test_retry_after_or_backoff_prefers_retry_after(self):
        delay = retry_after_or_backoff({"Retry-After": "2.5"}, 3, base=1.0, cap=10.0, jitter=0.0)
        self.assertEqual(delay, 2.5)

    def test_retry_after_or_backoff_caps_retry_after(self):
        delay = retry_after_or_backoff({"Retry-After": "120"}, 0, base=1.0, cap=10.0, jitter=0.0)
        self.assertEqual(delay, 10.0)


if __name__ == "__main__":
    unittest.main()
