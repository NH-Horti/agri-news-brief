import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import collector


class _DummyResponse:
    def __init__(self, status_code=200, payload=None, headers=None):
        self.status_code = status_code
        self._payload = payload if payload is not None else {"items": []}
        self.headers = headers or {}
        self.url = "https://openapi.naver.com"
        self.text = ""

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

    def get(self, *args, **kwargs):
        if not self.responses:
            raise AssertionError("unexpected get")
        return self.responses.pop(0)


class _DummyLogger:
    def __init__(self):
        self.warn_count = 0
        self.error_count = 0

    def warning(self, *args, **kwargs):
        self.warn_count += 1

    def error(self, *args, **kwargs):
        self.error_count += 1


class TestCollectorModule(unittest.TestCase):
    def test_naver_news_search_requires_credentials(self):
        cfg = collector.NaverClientConfig(client_id="", client_secret="")

        with self.assertRaises(RuntimeError):
            collector.naver_news_search(
                cfg=cfg,
                query="q",
                session_factory=lambda: _DummySession([]),
                throttle_fn=lambda: None,
                logger=_DummyLogger(),
                log_http_error=lambda *_: None,
            )

    def test_naver_news_search_retries_rate_limit(self):
        cfg = collector.NaverClientConfig(client_id="id", client_secret="sec", max_retries=2, backoff_max_sec=3.0)
        session = _DummySession(
            [
                _DummyResponse(429, {"items": [], "errorCode": "012", "errorMessage": "rate"}, headers={"Retry-After": "1"}),
                _DummyResponse(200, {"items": [{"title": "ok"}]}, headers={}),
            ]
        )
        logger = _DummyLogger()
        sleeps = []

        old_sleep = collector.time.sleep
        try:
            collector.time.sleep = lambda sec: sleeps.append(sec)
            out = collector.naver_news_search(
                cfg=cfg,
                query="q",
                session_factory=lambda: session,
                throttle_fn=lambda: None,
                logger=logger,
                log_http_error=lambda *_: None,
            )
        finally:
            collector.time.sleep = old_sleep

        self.assertEqual(len(out.get("items", [])), 1)
        self.assertEqual(sleeps, [1.0])
        self.assertGreaterEqual(logger.warn_count, 1)

    def test_naver_news_search_auth_error_fails_without_retry(self):
        cfg = collector.NaverClientConfig(client_id="id", client_secret="sec", max_retries=4, backoff_max_sec=3.0)
        session = _DummySession(
            [
                _DummyResponse(401, {"items": [], "errorCode": "024", "errorMessage": "Authentication failed"}),
                _DummyResponse(200, {"items": [{"title": "should-not-run"}]}),
            ]
        )
        logger = _DummyLogger()
        sleeps = []
        http_errors = []

        old_sleep = collector.time.sleep
        try:
            collector.time.sleep = lambda sec: sleeps.append(sec)
            with self.assertRaisesRegex(RuntimeError, "NAVER auth failed"):
                collector.naver_news_search(
                    cfg=cfg,
                    query="q",
                    session_factory=lambda: session,
                    throttle_fn=lambda: None,
                    logger=logger,
                    log_http_error=lambda *args: http_errors.append(args),
                )
        finally:
            collector.time.sleep = old_sleep

        self.assertEqual(sleeps, [])
        self.assertEqual(len(http_errors), 1)
        self.assertEqual(len(session.responses), 1)
        self.assertEqual(logger.warn_count, 0)
        self.assertEqual(logger.error_count, 0)

    def test_naver_news_search_paged_merges_and_stops(self):
        cfg = collector.NaverClientConfig(client_id="id", client_secret="sec")
        session = _DummySession(
            [
                _DummyResponse(200, {"items": [{"title": "a"}, {"title": "b"}]}),
                _DummyResponse(200, {"items": [{"title": "c"}]}),
            ]
        )

        out = collector.naver_news_search_paged(
            cfg=cfg,
            query="q",
            display=2,
            pages=3,
            session_factory=lambda: session,
            throttle_fn=lambda: None,
            logger=_DummyLogger(),
            log_http_error=lambda *_: None,
        )

        self.assertEqual([it.get("title") for it in out.get("items", [])], ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
