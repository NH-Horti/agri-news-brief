import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io_github


FIXTURES = ROOT / "tests" / "fixtures"


class _DummyResponse:
    def __init__(self, status_code, payload, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.headers = headers or {}
        self.url = "https://api.github.com"
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
    def __init__(self, get_responses=None, put_responses=None):
        self.get_responses = list(get_responses or [])
        self.put_responses = list(put_responses or [])

    def get(self, *args, **kwargs):
        if not self.get_responses:
            raise AssertionError("unexpected get")
        return self.get_responses.pop(0)

    def put(self, *args, **kwargs):
        if not self.put_responses:
            raise AssertionError("unexpected put")
        return self.put_responses.pop(0)


class _DummyLogger:
    def warning(self, *args, **kwargs):
        pass


class TestIoGithubContract(unittest.TestCase):
    def test_get_file_contract(self):
        payload = json.loads((FIXTURES / "github_content_file.json").read_text(encoding="utf-8"))
        session = _DummySession(get_responses=[_DummyResponse(200, payload)])

        raw, sha = io_github.github_get_file(
            "org/repo",
            "docs/a.txt",
            "token",
            session_factory=lambda: session,
            log_http_error=lambda *_: None,
        )

        self.assertEqual(raw, "hello")
        self.assertEqual(sha, "sha-123")

    def test_list_dir_contract(self):
        payload = json.loads((FIXTURES / "github_dir_list.json").read_text(encoding="utf-8"))
        session = _DummySession(get_responses=[_DummyResponse(200, payload)])

        out = io_github.github_list_dir(
            "org/repo",
            "docs/archive",
            "token",
            session_factory=lambda: session,
            log_http_error=lambda *_: None,
        )

        self.assertIsInstance(out, list)
        self.assertEqual(out[0].get("name"), "2026-03-07.html")

    def test_put_file_contract_with_retry_after(self):
        success = json.loads((FIXTURES / "github_put_success.json").read_text(encoding="utf-8"))
        session = _DummySession(
            put_responses=[
                _DummyResponse(429, {"message": "slow"}, headers={"Retry-After": "2"}),
                _DummyResponse(200, success),
            ]
        )

        sleeps = []
        old_sleep = io_github.time.sleep
        try:
            io_github.time.sleep = lambda sec: sleeps.append(sec)
            out = io_github.github_put_file(
                "org/repo",
                "docs/a.txt",
                "hello",
                "token",
                "msg",
                session_factory=lambda: session,
                logger=_DummyLogger(),
                log_http_error=lambda *_: None,
            )
        finally:
            io_github.time.sleep = old_sleep

        self.assertIsInstance(out, dict)
        self.assertIn("content", out)
        self.assertEqual(sleeps, [2.0])


if __name__ == "__main__":
    unittest.main()
