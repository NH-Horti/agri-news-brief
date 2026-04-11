import os
import tempfile
from datetime import datetime
from pathlib import Path
from unittest import TestCase
from unittest.mock import patch

import main
import replay


class LocalRuntimeTests(TestCase):
    def _make_article(
        self,
        section: str = "supply",
        title: str = "사과 가격 상승... 출하 물량 감소에 수급 비상",
        description: str = "사과 출하 물량 감소로 도매가격 상승세가 이어지고 있다.",
        link: str = "https://www.news1.kr/economy/food/999001",
        press: str = "뉴스1",
        topic: str = "사과",
    ) -> main.Article:
        canon = main.canonicalize_url(link)
        title_key = main.norm_title_key(title)
        return main.Article(
            section=section,
            title=title,
            description=description,
            link=link,
            originallink=link,
            pub_dt_kst=datetime(2026, 3, 20, 7, 0, tzinfo=main.KST),
            domain=main.domain_of(link),
            press=press,
            norm_key=main.make_norm_key(canon, press, title_key),
            title_key=title_key,
            canon_url=canon,
            topic=topic,
            score=11.0,
            source_query="사과 수급",
            source_channel="naver_news",
        )

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

    def test_article_snapshot_roundtrip_preserves_fields(self) -> None:
        article = self._make_article()
        article.summary = "사과 수급과 가격 흐름을 다룬 핵심 기사다."
        article.selection_stage = "supply_core"
        article.selection_note = "program_core"
        article.selection_fit_score = 3.4
        article.reassigned_from = "dist"

        payload = replay.article_to_snapshot_dict(article)
        restored = main.Article(**replay.article_dict_to_kwargs(payload))

        self.assertEqual(restored.title, article.title)
        self.assertEqual(restored.summary, article.summary)
        self.assertEqual(restored.selection_stage, article.selection_stage)
        self.assertEqual(restored.reassigned_from, article.reassigned_from)
        self.assertEqual(restored.pub_dt_kst, article.pub_dt_kst)

    def test_save_and_load_replay_snapshot_roundtrip(self) -> None:
        article = self._make_article()
        summary_cache = {
            article.norm_key: {
                "s": "사과 가격 상승과 출하 감소를 다룬 요약",
                "t": "2026-03-20T07:10:00+09:00",
            }
        }
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
                saved = main.save_replay_snapshot(
                    "2026-03-20",
                    datetime(2026, 3, 19, 7, 0, tzinfo=main.KST),
                    datetime(2026, 3, 20, 7, 0, tzinfo=main.KST),
                    {"supply": [article]},
                    summary_cache=summary_cache,
                    debug_payload={"collections": {"supply": {"items_total": 1}}},
                )
                self.assertTrue(saved.is_file())

                raw_by_section, start_kst, end_kst, loaded_cache, debug_payload, loaded_path = main.load_replay_snapshot("2026-03-20")
                self.assertEqual(loaded_path, saved)
                self.assertEqual(start_kst.isoformat(), "2026-03-19T07:00:00+09:00")
                self.assertEqual(end_kst.isoformat(), "2026-03-20T07:00:00+09:00")
                self.assertEqual(raw_by_section["supply"][0].title, article.title)
                self.assertEqual(loaded_cache[article.norm_key]["s"], summary_cache[article.norm_key]["s"])
                self.assertEqual(debug_payload["collections"]["supply"]["items_total"], 1)

    def test_build_sections_for_report_replay_uses_snapshot_summary_cache(self) -> None:
        article = self._make_article()
        snapshot_path: Path
        with tempfile.TemporaryDirectory() as td:
            snapshot_path = Path(td) / "2026-03-20.snapshot.json"
            with patch.dict(
                os.environ,
                {
                    "REPLAY_SNAPSHOT_PATH": str(snapshot_path),
                    "REPLAY_WRITE_SNAPSHOT": "false",
                },
                clear=False,
            ):
                main.save_replay_snapshot(
                    "2026-03-20",
                    datetime(2026, 3, 19, 7, 0, tzinfo=main.KST),
                    datetime(2026, 3, 20, 7, 0, tzinfo=main.KST),
                    {"supply": [article]},
                    summary_cache={
                        article.norm_key: {
                            "s": "리플레이 스냅샷에서 가져온 요약",
                            "t": "2026-03-20T07:15:00+09:00",
                        }
                    },
                )

                with patch.object(main, "load_summary_cache", return_value={}):
                    by_section, summary_cache, start_kst, end_kst = main._build_sections_for_report(
                        "NH-Horti/agri-news-brief",
                        "",
                        "2026-03-20",
                        datetime.min.replace(tzinfo=main.KST),
                        datetime.min.replace(tzinfo=main.KST),
                        allow_openai=False,
                        replay_snapshot=True,
                    )

                self.assertEqual(start_kst.isoformat(), "2026-03-19T07:00:00+09:00")
                self.assertEqual(end_kst.isoformat(), "2026-03-20T07:00:00+09:00")
                self.assertTrue(by_section["supply"])
                self.assertEqual(by_section["supply"][0].summary, "리플레이 스냅샷에서 가져온 요약")
                self.assertEqual(summary_cache[article.norm_key]["s"], "리플레이 스냅샷에서 가져온 요약")

    def test_load_openai_summary_feedback_reads_file(self) -> None:
        with tempfile.TemporaryDirectory() as td:
            feedback_path = Path(td) / "latest-feedback.txt"
            feedback_path.write_text("- keep the first sentence concrete\n- retain one number\n", encoding="utf-8")
            with patch.object(main, "OPENAI_SUMMARY_FEEDBACK_PATH", str(feedback_path)):
                with patch.object(main, "OPENAI_SUMMARY_FEEDBACK_MAX_CHARS", 80):
                    feedback = main._load_openai_summary_feedback()
            self.assertIn("first sentence", feedback)
            self.assertIn("retain one number", feedback)
