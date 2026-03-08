import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


class TestBranchIsolation(unittest.TestCase):
    def test_github_get_file_uses_configured_content_ref_for_default_main(self):
        called = {}

        old_ref = main.GH_CONTENT_REF
        old_get = main._io_github_get_file
        try:
            main.GH_CONTENT_REF = "develop"

            def _fake_get(repo, path, token, *, ref, session_factory, log_http_error):
                called["ref"] = ref
                return None, None

            main._io_github_get_file = _fake_get
            main.github_get_file("org/repo", "docs/index.html", "token", ref="main")
        finally:
            main.GH_CONTENT_REF = old_ref
            main._io_github_get_file = old_get

        self.assertEqual(called.get("ref"), "develop")

    def test_github_put_file_uses_configured_content_branch_for_default_main(self):
        called = {}

        old_branch = main.GH_CONTENT_BRANCH
        old_put = main._io_github_put_file
        try:
            main.GH_CONTENT_BRANCH = "develop"

            def _fake_put(repo, path, content, token, message, *, sha, branch, session_factory, logger, log_http_error, strip_html_fn):
                called["branch"] = branch
                return {"ok": True}

            main._io_github_put_file = _fake_put
            main.github_put_file("org/repo", "docs/index.html", "<html></html>", "token", "msg", branch="main")
        finally:
            main.GH_CONTENT_BRANCH = old_branch
            main._io_github_put_file = old_put

        self.assertEqual(called.get("branch"), "develop")


if __name__ == "__main__":
    unittest.main()
