import json
import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


class _FakeResponse:
    def __init__(self, text: str, ok: bool = True):
        self.text = text
        self.ok = ok


class _FakeSession:
    def __init__(self, get_text: str = "", post_text: str = ""):
        self._get_text = get_text
        self._post_text = post_text

    def get(self, *_args, **_kwargs):
        return _FakeResponse(self._get_text, ok=True)

    def post(self, *_args, **_kwargs):
        return _FakeResponse(self._post_text, ok=True)


class TestHistoricalRecall(unittest.TestCase):
    def test_should_use_google_news_recall_for_old_window(self):
        old_end = datetime.now(main.KST) - timedelta(days=main.GOOGLE_NEWS_RECALL_MIN_AGE_DAYS + 1)
        new_end = datetime.now(main.KST) - timedelta(days=1)
        self.assertTrue(main.should_use_google_news_recall(old_end))
        self.assertFalse(main.should_use_google_news_recall(new_end))

    def test_build_google_news_rss_search_url_adds_date_range(self):
        start = datetime(2026, 1, 2, 7, 0, tzinfo=main.KST)
        end = datetime(2026, 1, 5, 7, 0, tzinfo=main.KST)
        url = main.build_google_news_rss_search_url("사과 가격", start, end)
        self.assertIn("after%3A2026-01-01", url)
        self.assertIn("before%3A2026-01-06", url)
        self.assertIn("hl=ko&gl=KR&ceid=KR:ko", url)

    def test_decode_google_news_url_restores_original_link(self):
        html = '<c-wiz><div jscontroller="X" data-n-a-sg="SIG123" data-n-a-ts="1700"></div></c-wiz>'
        payload = json.dumps([[None, None, json.dumps([None, "https://example.com/article?utm_source=test"]) ]])
        fake = _FakeSession(get_text=html, post_text="\n\n" + payload)
        src = "https://news.google.com/rss/articles/CBMiTESTTOKEN?oc=5"
        with patch.object(main, "http_session", return_value=fake):
            main._GOOGLE_NEWS_DECODE_CACHE.clear()
            decoded = main.decode_google_news_url(src)
        self.assertEqual(decoded, "https://example.com/article")

    def test_fetch_google_news_search_items_parses_source_and_title(self):
        rss = """
        <rss><channel>
          <item>
            <title>사과 경매 활기 - 농민신문</title>
            <link>https://news.google.com/rss/articles/CBMiABC?oc=5</link>
            <pubDate>Tue, 06 Jan 2026 08:00:00 GMT</pubDate>
            <description><![CDATA[<a href="https://news.google.com/rss/articles/CBMiABC?oc=5">사과 경매 활기</a>&nbsp;&nbsp;<font color="#6f6f6f">농민신문</font>]]></description>
            <source>농민신문</source>
          </item>
        </channel></rss>
        """
        fake = _FakeSession(get_text=rss)
        start = datetime(2026, 1, 2, 7, 0, tzinfo=main.KST)
        end = datetime(2026, 1, 5, 7, 0, tzinfo=main.KST)
        with patch.object(main, "http_session", return_value=fake):
            with patch.object(main, "decode_google_news_url", return_value="https://www.nongmin.com/article/20260105000123"):
                rows = main.fetch_google_news_search_items("사과 경매", start, end, item_cap=3)
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]["title"], "사과 경매 활기")
        self.assertEqual(rows[0]["source"], "농민신문")
        self.assertEqual(rows[0]["link"], "https://www.nongmin.com/article/20260105000123")


if __name__ == "__main__":
    unittest.main()
