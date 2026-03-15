import sys
import unittest
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


class TestCommodityBoard(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conf = {s["key"]: s for s in main.SECTIONS}
        cls.now = datetime.now(main.KST)

    def _make_article(self, section: str, title: str, desc: str, url: str) -> main.Article:
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        canon = main.canonicalize_url(url)
        title_key = main.norm_title_key(title)
        return main.Article(
            section=section,
            title=title,
            description=desc,
            link=url,
            originallink=url,
            pub_dt_kst=self.now,
            domain=dom,
            press=press,
            norm_key=main.make_norm_key(canon, press, title_key),
            title_key=title_key,
            canon_url=canon,
            topic=main.extract_topic(title, desc),
            score=main.compute_rank_score(title, desc, dom, self.now, self.conf[section], press),
        )

    def test_managed_commodity_catalog_counts(self):
        self.assertEqual(len(main.MANAGED_COMMODITY_CATALOG), 33)
        self.assertEqual(sum(1 for item in main.MANAGED_COMMODITY_CATALOG if item.get("program_core")), 18)

    def test_radish_article_matches_board_item(self):
        article = self._make_article(
            "supply",
            "월동무 가격 강세… 산지 출하 조절 필요",
            "월동무 수급 불안으로 무 도매가격이 상승하고 산지 출하 조절 필요성이 커졌다.",
            "https://www.agrinet.co.kr/news/articleView.html?idxno=999001",
        )
        self.assertIn("radish", main.managed_commodity_keys_for_article(article))

    def test_managed_only_commodities_feed_supply_queries_and_topics(self):
        self.assertIn("무 수급", main.SUPPLY_ITEM_QUERIES)
        self.assertIn("양파 수급", main.SUPPLY_ITEM_QUERIES)
        self.assertIn("가지 가격", main.SUPPLY_ITEM_QUERIES)
        self.assertIn("무 가격", main.SUPPLY_ITEM_MUST_TERMS)
        self.assertIn("무 가격", dict(main.MANAGED_ONLY_COMMODITY_TOPICS)["무"])

    def test_program_core_board_item_uses_registry_topic(self):
        article = self._make_article(
            "supply",
            "샤인머스캣 작황 부진에 포도 수급 비상",
            "샤인머스캣 작황 부진과 저장 물량 감소로 포도 수급 불안이 커지고 있다.",
            "https://www.nongmin.com/article/20260315000001",
        )
        self.assertIn("grape", main.managed_commodity_keys_for_article(article))

    def test_board_context_marks_active_items(self):
        apple_article = self._make_article(
            "supply",
            "사과 가격 강세 지속… 저장 물량 관리 필요",
            "사과 저장 물량 감소와 출하 조절 이슈로 가격 강세가 이어지고 있다.",
            "https://www.news1.kr/economy/food/999001",
        )
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [apple_article]
        ctx = main.build_managed_commodity_board_context(by_section)
        apple = next(item for group in ctx["groups"] for item in group["items"] if item["key"] == "apple")
        self.assertTrue(apple["active"])
        self.assertEqual(apple["article_count"], 1)
        self.assertEqual(ctx["managed_total"], 33)
        self.assertEqual(ctx["program_total"], 18)
        self.assertEqual(ctx["active_total"], 1)
        self.assertNotIn("양배추", {item["label"] for group in ctx["groups"] for item in group["items"]})

    def test_managed_only_commodity_tags_are_emitted(self):
        tags = main._commodity_tags_in_text("월동무 가격 급등과 양파 수급 불안이 이어지고 있다.", limit=5)
        self.assertIn("무", tags)
        self.assertIn("양파", tags)

    def test_render_daily_page_includes_commodity_boards(self):
        apple_article = self._make_article(
            "supply",
            "사과 가격 강세 지속… 저장 물량 관리 필요",
            "사과 저장 물량 감소와 출하 조절 이슈로 가격 강세가 이어지고 있다.",
            "https://www.news1.kr/economy/food/999001",
        )
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [apple_article]
        html = main.render_daily_page(
            report_date="2026-03-15",
            start_kst=self.now,
            end_kst=self.now,
            by_section=by_section,
            archive_dates_desc=["2026-03-15"],
            site_path="https://example.com/agri-news-brief/",
        )
        self.assertIn("품목보드", html)
        self.assertIn("그날 기사와 연결된 품목만 류별로 보여드립니다.", html)
        self.assertIn('data-view-tab="briefing"', html)
        self.assertIn('data-view-tab="commodity"', html)
        self.assertIn("오늘 브리핑", html)
        self.assertIn("품목보드", html)
        self.assertIn("사과", html)
        self.assertNotIn("양배추", html)


if __name__ == "__main__":
    unittest.main()
