import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


class _DummyResponse:
    def __init__(self, status_code=200, payload=None, headers=None, url="https://kauth.kakao.com/oauth/token"):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}
        self.url = url
        self.text = str(self._payload)

    @property
    def ok(self):
        return 200 <= self.status_code < 300

    def json(self):
        return self._payload

    def raise_for_status(self):
        if not self.ok:
            raise RuntimeError(f"http status {self.status_code}")


class _DummySession:
    def __init__(self, responses):
        self.responses = list(responses)

    def post(self, *args, **kwargs):
        if not self.responses:
            raise AssertionError("unexpected post")
        return self.responses.pop(0)


class _DummyLogger:
    def __init__(self):
        self.warning_count = 0
        self.error_count = 0

    def warning(self, *args, **kwargs):
        self.warning_count += 1

    def error(self, *args, **kwargs):
        self.error_count += 1


class TestKakaoRuntimeBehavior(unittest.TestCase):
    def test_kakao_refresh_access_token_invalid_client_is_non_retryable(self):
        old_key = main.KAKAO_REST_API_KEY
        old_refresh = main.KAKAO_REFRESH_TOKEN
        old_secret = main.KAKAO_CLIENT_SECRET
        old_http_session = main.http_session
        try:
            main.KAKAO_REST_API_KEY = "bad-client"
            main.KAKAO_REFRESH_TOKEN = "bad-refresh"
            main.KAKAO_CLIENT_SECRET = ""
            session = _DummySession(
                [
                    _DummyResponse(
                        401,
                        {
                            "error": "invalid_client",
                            "error_description": "Not exist client_id",
                            "error_code": "KOE101",
                        },
                    )
                ]
            )
            main.http_session = lambda: session

            with self.assertRaises(main.KakaoNonRetryableError):
                main.kakao_refresh_access_token()
        finally:
            main.KAKAO_REST_API_KEY = old_key
            main.KAKAO_REFRESH_TOKEN = old_refresh
            main.KAKAO_CLIENT_SECRET = old_secret
            main.http_session = old_http_session

    def test_log_kakao_fail_open_uses_warning_for_non_retryable_error(self):
        old_log = main.log
        logger = _DummyLogger()
        try:
            main.log = logger
            main._log_kakao_fail_open(main.KakaoNonRetryableError("bad config"))
        finally:
            main.log = old_log

        self.assertEqual(logger.warning_count, 1)
        self.assertEqual(logger.error_count, 0)

    def test_log_kakao_fail_open_uses_error_for_generic_exception(self):
        old_log = main.log
        logger = _DummyLogger()
        try:
            main.log = logger
            main._log_kakao_fail_open(RuntimeError("boom"))
        finally:
            main.log = old_log

        self.assertEqual(logger.warning_count, 0)
        self.assertEqual(logger.error_count, 1)


if __name__ == "__main__":
    unittest.main()
