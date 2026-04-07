"""Tests for DedupeIndex, make_norm_key, load_state validation, and replay article validation."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main
import replay


class TestMakeNormKey(unittest.TestCase):
    """make_norm_key should produce stable, collision-resistant keys."""

    def test_url_based_key_uses_sha256(self):
        key = main.make_norm_key("https://example.com/article/123", "언론사", "titlekey")
        self.assertTrue(key.startswith("url:"))
        self.assertEqual(len(key), 4 + 32)  # "url:" + 32 hex chars

    def test_press_title_based_key_when_no_url(self):
        key = main.make_norm_key("", "언론사", "titlekey")
        self.assertTrue(key.startswith("pt:"))
        self.assertEqual(len(key), 3 + 32)

    def test_different_urls_produce_different_keys(self):
        k1 = main.make_norm_key("https://a.com/1", "", "")
        k2 = main.make_norm_key("https://a.com/2", "", "")
        self.assertNotEqual(k1, k2)

    def test_same_url_produces_same_key(self):
        k1 = main.make_norm_key("https://a.com/1", "p1", "t1")
        k2 = main.make_norm_key("https://a.com/1", "p2", "t2")
        self.assertEqual(k1, k2)  # URL takes precedence over press/title

    def test_empty_url_uses_press_and_title(self):
        k1 = main.make_norm_key("", "press_a", "title_x")
        k2 = main.make_norm_key("", "press_b", "title_x")
        self.assertNotEqual(k1, k2)


class TestDedupeIndex(unittest.TestCase):
    """DedupeIndex.add_and_check should correctly track seen articles."""

    def test_first_add_returns_true(self):
        idx = main.DedupeIndex()
        result = idx.add_and_check("https://a.com/1", "press", "tkey", "norm1")
        self.assertTrue(result)

    def test_duplicate_norm_key_returns_false(self):
        idx = main.DedupeIndex()
        idx.add_and_check("https://a.com/1", "press", "tkey", "norm1")
        result = idx.add_and_check("https://b.com/2", "press2", "tkey2", "norm1")
        self.assertFalse(result)

    def test_duplicate_canon_url_returns_false(self):
        idx = main.DedupeIndex()
        idx.add_and_check("https://a.com/1", "p1", "t1", "norm1")
        result = idx.add_and_check("https://a.com/1", "p2", "t2", "norm2")
        self.assertFalse(result)

    def test_duplicate_press_title_returns_false(self):
        idx = main.DedupeIndex()
        idx.add_and_check("https://a.com/1", "press", "tkey", "norm1")
        result = idx.add_and_check("https://b.com/2", "press", "tkey", "norm2")
        self.assertFalse(result)

    def test_empty_canon_url_skips_canon_check(self):
        idx = main.DedupeIndex()
        idx.add_and_check("", "p1", "t1", "norm1")
        # Different press+title but also empty URL
        result = idx.add_and_check("", "p2", "t2", "norm2")
        self.assertTrue(result)


class TestValidateState(unittest.TestCase):
    """_validate_state should fill defaults for missing/invalid keys."""

    def test_empty_dict_gets_defaults(self):
        result = main._validate_state({})
        self.assertIsNone(result["last_end_iso"])
        self.assertIsInstance(result["recent_items"], list)

    def test_valid_state_passes_through(self):
        state = {"last_end_iso": "2026-04-07T06:00:00+09:00", "recent_items": [{"canon": "x"}]}
        result = main._validate_state(state)
        self.assertEqual(result["last_end_iso"], "2026-04-07T06:00:00+09:00")
        self.assertEqual(len(result["recent_items"]), 1)

    def test_invalid_recent_items_reset(self):
        state = {"last_end_iso": None, "recent_items": "not_a_list"}
        result = main._validate_state(state)
        self.assertEqual(result["recent_items"], [])

    def test_invalid_keep_days_reset(self):
        state = {"last_end_iso": None, "recent_keep_days": "not_int"}
        result = main._validate_state(state)
        self.assertEqual(result["recent_keep_days"], 30)


class TestReplayArticleDictToKwargs(unittest.TestCase):
    """article_dict_to_kwargs should handle missing/corrupt data gracefully."""

    def test_valid_article_dict(self):
        data = {"title": "테스트 기사", "link": "https://test.com", "section": "supply",
                "score": 3.5, "is_core": True}
        kw = replay.article_dict_to_kwargs(data)
        self.assertEqual(kw["title"], "테스트 기사")
        self.assertEqual(kw["link"], "https://test.com")
        self.assertEqual(kw["score"], 3.5)
        self.assertTrue(kw["is_core"])

    def test_empty_dict_fills_defaults(self):
        kw = replay.article_dict_to_kwargs({})
        self.assertEqual(kw["title"], "")
        self.assertEqual(kw["link"], "")
        self.assertEqual(kw["score"], 0.0)
        self.assertFalse(kw["is_core"])

    def test_non_dict_input_returns_defaults(self):
        kw = replay.article_dict_to_kwargs("not_a_dict")
        self.assertEqual(kw["title"], "")

    def test_none_values_become_empty_string(self):
        kw = replay.article_dict_to_kwargs({"title": None, "link": None})
        self.assertEqual(kw["title"], "")
        self.assertEqual(kw["link"], "")


class TestNormStoryText(unittest.TestCase):
    """_norm_story_text should normalize Korean/English text consistently."""

    def test_basic_normalization(self):
        result = main._norm_story_text("사과 가격 10% 상승", "수급 불안")
        self.assertIn("사과", result)
        self.assertIn("가격", result)
        self.assertNotIn(" ", result)  # spaces removed

    def test_special_chars_removed(self):
        result = main._norm_story_text("[속보] 농산물 가격!!!", "")
        self.assertNotIn("[", result)
        self.assertNotIn("!", result)

    def test_empty_input(self):
        result = main._norm_story_text("", "")
        self.assertEqual(result, "")


if __name__ == "__main__":
    unittest.main()
