import os
import tempfile
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import main


class LocalRuntimeTests(TestCase):
    def test_load_env_file_preserves_existing_values(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            env_path = Path(td) / ".env.local"
            env_path.write_text(
                "\n".join(
                    [
                        "NAVER_CLIENT_ID=from_file",
                        'QUOTED_VALUE="alpha beta"',
                        "INLINE_COMMENT=value # ignored",
                        "export EXTRA_VALUE=' spaced value '",
                    ]
                ),
                encoding="utf-8",
            )
            with patch.dict(os.environ, {"NAVER_CLIENT_ID": "keep_me"}, clear=False):
                loaded = main._load_env_file(env_path)
                self.assertEqual(os.environ["NAVER_CLIENT_ID"], "keep_me")
                self.assertEqual(os.environ["QUOTED_VALUE"], "alpha beta")
                self.assertEqual(os.environ["INLINE_COMMENT"], "value")
                self.assertEqual(os.environ["EXTRA_VALUE"], " spaced value ")
                self.assertEqual(loaded["NAVER_CLIENT_ID"], "from_file")

    def test_local_dry_run_github_wrappers_use_output_directory(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            out_dir = Path(td) / "out"
            with patch.dict(
                os.environ,
                {
                    "LOCAL_DRY_RUN": "true",
                    "LOCAL_OUTPUT_DIR": str(out_dir),
                },
                clear=False,
            ):
                main.github_put_file(
                    "NH-Horti/agri-news-brief",
                    "docs/dev/index.html",
                    "<html>preview</html>",
                    token="",
                    message="local write",
                    branch="codex/dev-preview",
                )
                target = out_dir / "codex" / "dev-preview" / "docs" / "dev" / "index.html"
                self.assertTrue(target.is_file())

                raw, sha = main.github_get_file(
                    "NH-Horti/agri-news-brief",
                    "docs/dev/index.html",
                    token="",
                    ref="codex/dev-preview",
                )
                self.assertEqual(raw, "<html>preview</html>")
                self.assertTrue(sha)

                items = main.github_list_dir(
                    "NH-Horti/agri-news-brief",
                    "docs/dev",
                    token="",
                    ref="codex/dev-preview",
                )
                self.assertTrue(any(item["name"] == "index.html" for item in items))
