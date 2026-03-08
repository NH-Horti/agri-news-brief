import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


class TestRuntimeGuards(unittest.TestCase):
    def test_dev_single_page_write_guard_blocks_non_preview_path(self):
        old_mode = main.DEV_SINGLE_PAGE_MODE
        old_path = main.DEV_SINGLE_PAGE_PATH
        old_put = main._io_github_put_file
        try:
            main.DEV_SINGLE_PAGE_MODE = True
            main.DEV_SINGLE_PAGE_PATH = "docs/dev/index.html"

            def _fake_put(repo, path, content, token, message, *, sha, branch, session_factory, logger, log_http_error, strip_html_fn):
                return {"ok": True}

            main._io_github_put_file = _fake_put

            with self.assertRaises(RuntimeError):
                main.github_put_file("org/repo", "docs/index.html", "<html></html>", "token", "msg")
        finally:
            main.DEV_SINGLE_PAGE_MODE = old_mode
            main.DEV_SINGLE_PAGE_PATH = old_path
            main._io_github_put_file = old_put

    def test_dev_single_page_write_guard_allows_preview_path(self):
        old_mode = main.DEV_SINGLE_PAGE_MODE
        old_path = main.DEV_SINGLE_PAGE_PATH
        old_put = main._io_github_put_file
        called = {}
        try:
            main.DEV_SINGLE_PAGE_MODE = True
            main.DEV_SINGLE_PAGE_PATH = "docs/dev/index.html"

            def _fake_put(repo, path, content, token, message, *, sha, branch, session_factory, logger, log_http_error, strip_html_fn):
                called["path"] = path
                called["branch"] = branch
                return {"ok": True}

            main._io_github_put_file = _fake_put
            main.github_put_file("org/repo", "docs/dev/index.html", "<html></html>", "token", "msg", branch="main")
        finally:
            main.DEV_SINGLE_PAGE_MODE = old_mode
            main.DEV_SINGLE_PAGE_PATH = old_path
            main._io_github_put_file = old_put

        self.assertEqual(called.get("path"), "docs/dev/index.html")

    def test_output_url_healthcheck_validates_host_and_path_prefix(self):
        old_host = main.HEALTHCHECK_EXPECTED_HOST
        old_prefix = main.HEALTHCHECK_EXPECTED_PATH_PREFIX
        try:
            main.HEALTHCHECK_EXPECTED_HOST = "nh-horti.github.io"
            main.HEALTHCHECK_EXPECTED_PATH_PREFIX = "/agri-news-brief/dev"

            main._validate_output_url_healthcheck("https://nh-horti.github.io/agri-news-brief/dev/index.html?v=1")

            with self.assertRaises(RuntimeError):
                main._validate_output_url_healthcheck("https://example.com/agri-news-brief/dev/index.html")

            with self.assertRaises(RuntimeError):
                main._validate_output_url_healthcheck("https://nh-horti.github.io/agri-news-brief/archive/2026-03-08.html")
        finally:
            main.HEALTHCHECK_EXPECTED_HOST = old_host
            main.HEALTHCHECK_EXPECTED_PATH_PREFIX = old_prefix


if __name__ == "__main__":
    unittest.main()
