import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

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
        self.warnings = []

    def warning(self, *args, **kwargs):
        self.warning_count += 1
        self.warnings.append(args)

    def error(self, *args, **kwargs):
        self.error_count += 1


class TestKakaoRuntimeBehavior(unittest.TestCase):
    def test_write_kakao_send_status_writes_status_file(self):
        old_path = main.KAKAO_STATUS_FILE
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                status_path = Path(tmpdir) / "kakao-status.txt"
                main.KAKAO_STATUS_FILE = str(status_path)
                main._write_kakao_send_status("success")
                self.assertEqual(status_path.read_text(encoding="utf-8").strip(), "success")
        finally:
            main.KAKAO_STATUS_FILE = old_path

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

    def test_kakao_refresh_access_token_writes_renewed_refresh_token(self):
        old_key = main.KAKAO_REST_API_KEY
        old_refresh = main.KAKAO_REFRESH_TOKEN
        old_secret = main.KAKAO_CLIENT_SECRET
        old_out_file = main.KAKAO_REFRESH_TOKEN_OUT_FILE
        old_http_session = main.http_session
        old_log = main.log
        logger = _DummyLogger()
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                out_path = Path(tmpdir) / "new-refresh-token.txt"
                main.KAKAO_REST_API_KEY = "client"
                main.KAKAO_REFRESH_TOKEN = "old-refresh"
                main.KAKAO_CLIENT_SECRET = ""
                main.KAKAO_REFRESH_TOKEN_OUT_FILE = str(out_path)
                main.log = logger
                session = _DummySession(
                    [
                        _DummyResponse(
                            200,
                            {
                                "access_token": "access",
                                "refresh_token": "new-refresh",
                            },
                        )
                    ]
                )
                main.http_session = lambda: session

                self.assertEqual(main.kakao_refresh_access_token(), "access")
                self.assertEqual(out_path.read_text(encoding="utf-8").strip(), "new-refresh")
                self.assertEqual(logger.warning_count, 1)
        finally:
            main.KAKAO_REST_API_KEY = old_key
            main.KAKAO_REFRESH_TOKEN = old_refresh
            main.KAKAO_CLIENT_SECRET = old_secret
            main.KAKAO_REFRESH_TOKEN_OUT_FILE = old_out_file
            main.http_session = old_http_session
            main.log = old_log

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

    def test_daily_summary_send_records_receipt_before_success_status(self):
        statuses = []
        with (
            patch.object(main, "_load_delivery_receipt", return_value={}),
            patch.object(main, "build_kakao_message", return_value="normal daily summary"),
            patch.object(main, "kakao_send_to_me") as send,
            patch.object(main, "_write_delivery_receipt") as write_receipt,
            patch.object(main, "_write_kakao_send_status", side_effect=statuses.append),
        ):
            status = main._send_kakao_daily_summary(
                "owner/repo",
                "token",
                "2026-07-29",
                "https://example.com/archive/2026-07-29.html",
                {},
                publication_mode="maintenance_replay_date",
            )

        self.assertEqual(status, "success")
        send.assert_called_once_with(
            "normal daily summary",
            "https://example.com/archive/2026-07-29.html",
        )
        write_receipt.assert_called_once()
        self.assertEqual(statuses, ["success"])

    def test_daily_summary_send_suppresses_duplicate_from_receipt(self):
        receipt = {"report_date": "2026-07-29", "status": "success", "channel": "kakao"}
        with (
            patch.object(main, "_load_delivery_receipt", return_value=receipt),
            patch.object(main, "kakao_send_to_me") as send,
            patch.object(main, "_write_kakao_send_status") as write_status,
        ):
            status = main._send_kakao_daily_summary(
                "owner/repo",
                "token",
                "2026-07-29",
                "https://example.com/archive/2026-07-29.html",
                {},
                publication_mode="normal",
            )

        self.assertEqual(status, "already_delivered")
        send.assert_not_called()
        write_status.assert_called_once_with("already_delivered")

    def test_daily_summary_send_does_not_report_success_when_receipt_write_fails(self):
        with (
            patch.object(main, "KAKAO_FAIL_OPEN", True),
            patch.object(main, "_load_delivery_receipt", return_value={}),
            patch.object(main, "build_kakao_message", return_value="normal daily summary"),
            patch.object(main, "kakao_send_to_me"),
            patch.object(main, "_write_delivery_receipt", side_effect=RuntimeError("write failed")),
            patch.object(main, "_write_kakao_send_status") as write_status,
        ):
            status = main._send_kakao_daily_summary(
                "owner/repo",
                "token",
                "2026-07-29",
                "https://example.com/archive/2026-07-29.html",
                {},
                publication_mode="maintenance_replay_date",
            )

        self.assertEqual(status, "sent_receipt_failed")
        write_status.assert_called_once_with("sent_receipt_failed")


if __name__ == "__main__":
    unittest.main()
