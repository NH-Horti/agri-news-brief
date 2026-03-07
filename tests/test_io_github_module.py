import base64
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import io_github


class _DummyResponse:
    def __init__(self, status_code=200, payload=None, headers=None, text=""):
        self.status_code = status_code
        self._payload = payload if payload is not None else {}
        self.headers = headers or {}
        self.text = text
        self.url = "https://api.github.test"

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
        self._get_responses = list(get_responses or [])
        self._put_responses = list(put_responses or [])
        self.put_calls = []

    def get(self, *args, **kwargs):
        if not self._get_responses:
            raise AssertionError("unexpected get")
        return self._get_responses.pop(0)

    def put(self, *args, **kwargs):
        self.put_calls.append(kwargs)
        if not self._put_responses:
            raise AssertionError("unexpected put")
        return self._put_responses.pop(0)


class _DummyLogger:
    def warning(self, *args, **kwargs):
        pass


class TestIoGithubModule(unittest.TestCase):
    def test_github_get_file_decodes_base64(self):
        raw = "hello"
        encoded = base64.b64encode(raw.encode("utf-8")).decode("utf-8")
        session = _DummySession(get_responses=[_DummyResponse(200, {"content": encoded, "sha": "abc"})])

        out_raw, out_sha = io_github.github_get_file(
            "org/repo",
            "docs/a.txt",
            "token",
            session_factory=lambda: session,
            log_http_error=lambda *_: None,
        )

        self.assertEqual(out_raw, raw)
        self.assertEqual(out_sha, "abc")

    def test_github_list_dir_returns_empty_on_404(self):
        session = _DummySession(get_responses=[_DummyResponse(404, {})])

        out = io_github.github_list_dir(
            "org/repo",
            "docs",
            "token",
            session_factory=lambda: session,
            log_http_error=lambda *_: None,
        )

        self.assertEqual(out, [])

    def test_github_put_file_refreshes_sha_on_conflict(self):
        session = _DummySession(
            put_responses=[
                _DummyResponse(409, {}),
                _DummyResponse(200, {"ok": True}),
            ]
        )

        old_get = io_github.github_get_file
        try:
            io_github.github_get_file = lambda *args, **kwargs: ("", "new-sha")
            out = io_github.github_put_file(
                "org/repo",
                "docs/a.txt",
                "hello",
                "token",
                "msg",
                sha="old-sha",
                session_factory=lambda: session,
                logger=_DummyLogger(),
                log_http_error=lambda *_: None,
            )
        finally:
            io_github.github_get_file = old_get

        self.assertTrue(out.get("ok"))
        self.assertEqual(len(session.put_calls), 2)
        self.assertEqual(session.put_calls[1]["json"].get("sha"), "new-sha")

    def test_github_put_file_uses_retry_after(self):
        session = _DummySession(
            put_responses=[
                _DummyResponse(429, {}, headers={"Retry-After": "1.5"}),
                _DummyResponse(200, {"ok": True}),
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

        self.assertTrue(out.get("ok"))
        self.assertEqual(sleeps, [1.5])


if __name__ == "__main__":
    unittest.main()