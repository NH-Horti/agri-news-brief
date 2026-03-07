import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import collector


FIXTURES = ROOT / "tests" / "fixtures"


class _DummyResponse:
    def __init__(self, status_code, payload, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.url = "https://openapi.naver.com"
        self.text = json.dumps(payload, ensure_ascii=False)

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
    def warning(self, *args, **kwargs):
        pass

    def error(self, *args, **kwargs):
        pass


class TestCollectorContract(unittest.TestCase):
    def test_rate_limited_contract_then_success(self):
        limited = json.loads((FIXTURES / "naver_rate_limited_payload.json").read_text(encoding="utf-8"))
        success = json.loads((FIXTURES / "naver_success_payload.json").read_text(encoding="utf-8"))

        session = _DummySession(
            [
                _DummyResponse(429, limited, headers={"Retry-After": "1"}),
                _DummyResponse(200, success),
            ]
        )

        sleeps = []
        old_sleep = collector.time.sleep
        try:
            collector.time.sleep = lambda sec: sleeps.append(sec)
            out = collector.naver_news_search(
                cfg=collector.NaverClientConfig(client_id="id", client_secret="sec", max_retries=2),
                query="agri",
                session_factory=lambda: session,
                throttle_fn=lambda: None,
                logger=_DummyLogger(),
                log_http_error=lambda *_: None,
            )
        finally:
            collector.time.sleep = old_sleep

        self.assertIsInstance(out, dict)
        self.assertIn("items", out)
        self.assertIsInstance(out["items"], list)
        self.assertEqual(len(out["items"]), 1)
        self.assertEqual(sleeps, [1.0])


if __name__ == "__main__":
    unittest.main()
