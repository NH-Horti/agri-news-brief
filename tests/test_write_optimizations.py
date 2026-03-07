import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


class TestWriteOptimizations(unittest.TestCase):
    def test_github_put_file_if_changed_skips_when_unchanged(self):
        calls = []

        old_get = main.github_get_file
        old_put = main.github_put_file
        try:
            main.github_get_file = lambda repo, path, token, ref="main": ('{"k":1}\n', "sha-1")

            def _fake_put(repo, path, content, token, message, sha=None, branch="main"):
                calls.append((repo, path, sha, branch))
                return {"ok": True}

            main.github_put_file = _fake_put

            wrote = main.github_put_file_if_changed(
                "org/repo",
                ".agri_state.json",
                '{"k":1}\n',
                "token",
                "Update state",
            )
        finally:
            main.github_get_file = old_get
            main.github_put_file = old_put

        self.assertFalse(wrote)
        self.assertEqual(calls, [])

    def test_save_docs_archive_manifest_skips_when_dates_unchanged(self):
        old_payload = {
            "version": 1,
            "updated_at_kst": "2026-03-07T10:00:00+09:00",
            "dates": ["2026-03-06", "2026-03-05"],
        }
        old_raw = json.dumps(old_payload, ensure_ascii=False, indent=2)
        put_calls = []

        old_get = main.github_get_file
        old_put = main.github_put_file
        try:
            def _fake_get(repo, path, token, ref="main"):
                if path == main.DOCS_ARCHIVE_MANIFEST_JSON_PATH:
                    return old_raw, "sha-old"
                return None, None

            def _fake_put(repo, path, content, token, message, sha=None, branch="main"):
                put_calls.append((repo, path, sha, branch, message))
                return {"ok": True}

            main.github_get_file = _fake_get
            main.github_put_file = _fake_put

            wrote = main.save_docs_archive_manifest(
                "org/repo",
                "token",
                ["2026-03-05", "2026-03-06"],
            )
        finally:
            main.github_get_file = old_get
            main.github_put_file = old_put

        self.assertFalse(wrote)
        self.assertEqual(put_calls, [])

    def test_save_archive_manifest_refreshes_runtime_cache(self):
        repo = "org/repo"
        manifest = {"dates": ["2026-03-05", "2026-03-06"]}
        old_raw = json.dumps(main._normalize_manifest(manifest), ensure_ascii=False, indent=2)

        old_cache = dict(main._MANIFEST_DATES_DESC_CACHE)
        put_calls = []

        old_get = main.github_get_file
        old_put = main.github_put_file
        try:
            main._MANIFEST_DATES_DESC_CACHE.clear()

            def _fake_get(_repo, path, token, ref="main"):
                if path == main.ARCHIVE_MANIFEST_PATH:
                    return old_raw, "sha-old"
                return None, None

            def _fake_put(repo2, path, content, token, message, sha=None, branch="main"):
                put_calls.append((repo2, path, sha, branch))
                return {"ok": True}

            main.github_get_file = _fake_get
            main.github_put_file = _fake_put

            main.save_archive_manifest(repo, "token", manifest, "sha-old")
            self.assertEqual(put_calls, [])
            self.assertEqual(main._MANIFEST_DATES_DESC_CACHE.get(repo), ["2026-03-06", "2026-03-05"])
        finally:
            main.github_get_file = old_get
            main.github_put_file = old_put
            main._MANIFEST_DATES_DESC_CACHE.clear()
            main._MANIFEST_DATES_DESC_CACHE.update(old_cache)


if __name__ == "__main__":
    unittest.main()
