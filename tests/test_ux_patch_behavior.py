import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


class TestUxPatchBehavior(unittest.TestCase):
    def _run_patch(self, iso_date: str, raw_html: str):
        path = f"{main.DOCS_ARCHIVE_DIR}/{iso_date}.html"
        saved = {}

        old_get = main.github_get_file
        old_put = main.github_put_file
        old_nav_dates = main._get_ux_nav_dates_desc
        old_manifest_dates = main._get_manifest_dates_desc_cached

        try:
            def _fake_get(repo, file_path, token, ref="main"):
                if file_path == path:
                    return raw_html, "sha-test"
                return None, None

            def _fake_put(repo, file_path, content, token, message, sha=None, branch="main"):
                saved["path"] = file_path
                saved["content"] = content
                return {"content": {"path": file_path}}

            main.github_get_file = _fake_get
            main.github_put_file = _fake_put
            main._get_ux_nav_dates_desc = lambda repo, token: [iso_date]
            main._get_manifest_dates_desc_cached = lambda repo, token: [iso_date]

            ok = main.patch_archive_page_ux("org/repo", "token", iso_date, "/")
        finally:
            main.github_get_file = old_get
            main.github_put_file = old_put
            main._get_ux_nav_dates_desc = old_nav_dates
            main._get_manifest_dates_desc_cached = old_manifest_dates

        return ok, saved, path

    def test_patch_archive_page_ux_preserves_tail_after_nav_loading_insert(self):
        iso_date = "2026-03-06"
        raw_html = """
<html>
<head><title>ux patch test</title></head>
<body>
<div class="navRow"><a class="navBtn" href="/">아카이브</a></div>
<div class="wrap"><section id="sec-supply"><div class="secCount">1건</div></section></div>
<div id="tail">TAIL_SENTINEL</div>
</body>
</html>
""".strip()

        ok, saved, path = self._run_patch(iso_date, raw_html)

        self.assertTrue(ok)
        self.assertEqual(saved.get("path"), path)

        out = saved.get("content", "")
        self.assertIn('id="navLoading"', out)
        self.assertIn("TAIL_SENTINEL", out)

        lower = out.lower()
        self.assertIn("</body>", lower)
        self.assertIn("</html>", lower)

    def test_patch_archive_page_ux_keeps_swipe_ignore_attribute_idempotent(self):
        iso_date = "2026-03-06"
        raw_html = """
<html>
<head><title>ux patch test</title></head>
<body>
<div class="navRow"><a class="navBtn" href="/">아카이브</a></div>
<div class="chipbar" data-swipe-ignore="1">
  <div class="chipwrap">
    <div class="chips" data-swipe-ignore="1"></div>
  </div>
</div>
<div class="wrap"><section id="sec-supply"><div class="secCount">1건</div></section></div>
</body>
</html>
""".strip()

        ok, saved, _path = self._run_patch(iso_date, raw_html)

        self.assertTrue(ok)
        out = saved.get("content", "")

        self.assertRegex(out, r'class="chipbar"[^>]*data-swipe-ignore="1"')
        self.assertRegex(out, r'class="chips"[^>]*data-swipe-ignore="1"')
        self.assertNotRegex(out, r'class="chipbar"[^>]*data-swipe-ignore="1"[^>]*data-swipe-ignore="1"')
        self.assertNotRegex(out, r'class="chips"[^>]*data-swipe-ignore="1"[^>]*data-swipe-ignore="1"')


if __name__ == "__main__":
    unittest.main()
