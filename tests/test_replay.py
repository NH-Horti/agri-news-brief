"""replay.py 모듈 테스트 — 스냅샷 저장/로드 및 스키마 버전 검증."""
from __future__ import annotations

import json
import os
import tempfile
import unittest
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

from replay import (
    SNAPSHOT_SCHEMA_VERSION,
    SNAPSHOT_MIN_COMPAT_VERSION,
    SnapshotVersionError,
    article_to_snapshot_dict,
    article_dict_to_kwargs,
    extract_summary_cache_for_articles,
    save_snapshot,
    load_snapshot,
)

KST = timezone(timedelta(hours=9))


@dataclass
class _FakeArticle:
    """테스트용 Article 대체 클래스."""
    section: str = ""
    title: str = ""
    description: str = ""
    link: str = ""
    originallink: str = ""
    pub_dt_kst: datetime = datetime(2026, 3, 22, 9, 0, 0, tzinfo=KST)
    domain: str = ""
    press: str = ""
    norm_key: str = ""
    title_key: str = ""
    canon_url: str = ""
    topic: str = ""
    is_core: bool = False
    score: float = 0.0
    summary: str = ""
    forced_section: str = ""
    origin_section: str = ""
    source_query: str = ""
    source_channel: str = ""
    selection_stage: str = ""
    selection_note: str = ""
    selection_fit_score: float = 0.0
    reassigned_from: str = ""


def _make_article(**kw) -> _FakeArticle:
    return _FakeArticle(**kw)


def _article_factory(kw: dict) -> _FakeArticle:
    return _FakeArticle(**kw)


class TestArticleSerialization(unittest.TestCase):
    """Article ↔ dict 직렬화 왕복 테스트."""

    def test_roundtrip(self):
        original = _FakeArticle(
            section="supply",
            title="테스트 기사",
            description="설명",
            link="https://example.com/1",
            press="농민신문",
            norm_key="nk1",
            score=12.5,
        )
        d = article_to_snapshot_dict(original)
        kw = article_dict_to_kwargs(d)
        restored = _FakeArticle(**kw)

        self.assertEqual(restored.section, original.section)
        self.assertEqual(restored.title, original.title)
        self.assertEqual(restored.press, original.press)
        self.assertEqual(restored.score, original.score)
        self.assertEqual(restored.norm_key, original.norm_key)


class TestSnapshotSaveLoad(unittest.TestCase):
    """save_snapshot / load_snapshot 왕복 테스트."""

    def test_save_and_load_roundtrip(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "2026-03-22.snapshot.json"
            articles = {
                "supply": [_FakeArticle(section="supply", title="기사A", norm_key="a")],
                "policy": [],
            }
            save_snapshot(
                "2026-03-22",
                datetime(2026, 3, 22, 0, 0, tzinfo=KST),
                datetime(2026, 3, 22, 23, 59, tzinfo=KST),
                articles,
                ["supply", "policy"],
                summary_cache={"a": "요약문"},
                target=target,
            )

            self.assertTrue(target.is_file())

            raw, start, end, cache, debug, path = load_snapshot(
                "2026-03-22",
                ["supply", "policy"],
                _article_factory,
                target=target,
            )

            self.assertEqual(len(raw["supply"]), 1)
            self.assertEqual(raw["supply"][0].title, "기사A")
            self.assertEqual(cache.get("a"), "요약문")
            self.assertEqual(path, target)


class TestSchemaVersionValidation(unittest.TestCase):
    """스냅샷 스키마 버전 검증 테스트."""

    def _write_snapshot(self, tmpdir: str, version: int, report_date: str = "2026-03-22") -> Path:
        target = Path(tmpdir) / f"{report_date}.snapshot.json"
        payload = {
            "schema_version": version,
            "version": version,
            "report_date": report_date,
            "window": {
                "start_kst": "2026-03-22T00:00:00+09:00",
                "end_kst": "2026-03-22T23:59:00+09:00",
            },
            "raw_by_section": {"supply": [], "policy": []},
            "summary_cache": {},
            "debug": {},
        }
        target.write_text(json.dumps(payload), encoding="utf-8")
        return target

    def test_current_version_loads_ok(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = self._write_snapshot(tmpdir, SNAPSHOT_SCHEMA_VERSION)
            raw, *_ = load_snapshot(
                "2026-03-22", ["supply", "policy"], _article_factory, target=target,
            )
            self.assertIsInstance(raw, dict)

    def test_too_old_version_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = self._write_snapshot(tmpdir, SNAPSHOT_MIN_COMPAT_VERSION - 1)
            with self.assertRaises(SnapshotVersionError) as ctx:
                load_snapshot(
                    "2026-03-22", ["supply", "policy"], _article_factory, target=target,
                )
            self.assertIn("too old", str(ctx.exception))

    def test_zero_version_raises(self):
        """version 필드가 없는(0) 구 스냅샷은 거부."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = Path(tmpdir) / "2026-03-22.snapshot.json"
            payload = {
                "report_date": "2026-03-22",
                "window": {"start_kst": "", "end_kst": ""},
                "raw_by_section": {},
                "summary_cache": {},
                "debug": {},
            }
            target.write_text(json.dumps(payload), encoding="utf-8")
            with self.assertRaises(SnapshotVersionError):
                load_snapshot(
                    "2026-03-22", ["supply"], _article_factory, target=target,
                )

    def test_newer_version_warns_but_loads(self):
        """미래 버전은 경고만 하고 로드 시도."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target = self._write_snapshot(tmpdir, SNAPSHOT_SCHEMA_VERSION + 10)
            raw, *_ = load_snapshot(
                "2026-03-22", ["supply", "policy"], _article_factory, target=target,
            )
            self.assertIsInstance(raw, dict)

    def test_date_mismatch_raises(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            target = self._write_snapshot(tmpdir, SNAPSHOT_SCHEMA_VERSION, report_date="2026-03-21")
            with self.assertRaises(RuntimeError) as ctx:
                load_snapshot(
                    "2026-03-22", ["supply"], _article_factory, target=target,
                )
            self.assertIn("mismatch", str(ctx.exception))


class TestSummaryCacheExtraction(unittest.TestCase):
    def test_extracts_matching_keys(self):
        articles = {"supply": [_FakeArticle(norm_key="k1"), _FakeArticle(norm_key="k2")]}
        cache = {"k1": "요약1", "k2": {"s": "요약2", "t": "2026-01-01"}, "k3": "무관"}
        result = extract_summary_cache_for_articles(articles, cache)
        self.assertIn("k1", result)
        self.assertIn("k2", result)
        self.assertNotIn("k3", result)


if __name__ == "__main__":
    unittest.main()
