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

    def _item(self, key: str) -> dict:
        return main.MANAGED_COMMODITY_BY_KEY[key]

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
        item = self._item("radish")
        label = item["label"]
        article = self._make_article(
            "supply",
            f"{label} 가격 강세 지속",
            f"{label} 출하 조절과 수급 관리가 필요하다.",
            "https://www.agrinet.co.kr/news/articleView.html?idxno=999001",
        )
        self.assertIn("radish", main.managed_commodity_keys_for_article(article))

    def test_managed_only_commodities_feed_supply_queries_and_topics(self):
        radish = self._item("radish")
        onion = self._item("green_onion")
        eggplant = self._item("eggplant")

        for query in main._managed_commodity_supply_queries(radish):
            self.assertIn(query, main.SUPPLY_ITEM_QUERIES)
        for query in main._managed_commodity_supply_queries(onion):
            self.assertIn(query, main.SUPPLY_ITEM_QUERIES)
        for query in main._managed_commodity_supply_queries(eggplant):
            self.assertIn(query, main.SUPPLY_ITEM_QUERIES)

        for term in main._managed_commodity_must_terms(radish):
            self.assertIn(term, main.SUPPLY_ITEM_MUST_TERMS)

        topic_map = dict(main.MANAGED_ONLY_COMMODITY_TOPICS)
        self.assertIn(radish["label"], topic_map)
        self.assertTrue(topic_map[radish["label"]])

    def test_program_core_commodities_feed_pest_recall_queries(self):
        for key in ("green_onion", "apple", "tomato"):
            for query in main._managed_commodity_pest_queries(self._item(key)):
                self.assertIn(query, main.MANAGED_PEST_RECALL_QUERIES)

    def test_daily_pest_query_builder_spreads_beyond_first_few_core_items(self):
        queries = main.build_managed_pest_recall_queries(datetime(2026, 3, 15, tzinfo=main.KST))
        expected = [
            main._managed_commodity_pest_queries(self._item(key))[0]
            for key in ("onion", "apple", "tomato", "garlic")
        ]
        for query in expected:
            self.assertIn(query, queries)
        self.assertGreaterEqual(len(queries), len(main.MANAGED_PEST_PRIMARY_CORE_QUERIES))

    def test_program_core_board_item_uses_registry_topic(self):
        item = self._item("grape")
        label = item["short_label"]
        article = self._make_article(
            "supply",
            f"{label} 수급 불안에 가격 강세",
            f"{label} 출하 물량 감소로 가격 변동성이 커지고 있다.",
            "https://www.nongmin.com/article/20260315000001",
        )
        self.assertIn("grape", main.managed_commodity_keys_for_article(article))

    def test_board_context_marks_active_items(self):
        item = self._item("apple")
        label = item["short_label"]
        apple_article = self._make_article(
            "supply",
            f"{label} 가격 강세와 출하 조절",
            f"{label} 물량 감소로 가격 강세가 이어지고 있다.",
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
        seasoning_group = next(group for group in ctx["groups"] if group["key"] == "seasoning_veg")
        self.assertEqual(seasoning_group["active_count"], 0)
        self.assertEqual(seasoning_group["item_total"], 5)
        self.assertNotIn("붉은고추", {item["label"] for group in ctx["groups"] for item in group["items"]})

    def test_managed_only_commodity_tags_are_emitted(self):
        radish = self._item("radish")["short_label"]
        green_onion = self._item("green_onion")["short_label"]
        tags = main._commodity_tags_in_text(f"{radish} 가격 급등과 {green_onion} 수급 불안이 이어진다.", limit=5)
        self.assertIn(radish, tags)
        self.assertIn(green_onion, tags)

    def test_render_daily_page_includes_commodity_boards(self):
        item = self._item("apple")
        label = item["short_label"]
        apple_article = self._make_article(
            "supply",
            f"{label} 가격 강세와 출하 조절",
            f"{label} 물량 감소로 가격 강세가 이어지고 있다.",
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
        self.assertIn('data-view-tab="briefing"', html)
        self.assertIn('data-view-tab="commodity"', html)
        self.assertIn("오늘 브리핑", html)
        self.assertIn(label, html)
        self.assertIn("양념채소류", html)
        self.assertIn("활성 품목 0 / 5", html)
        self.assertIn('data-swipe-ignore="1"', html)
        self.assertNotIn("붉은고추", html)

    def test_render_daily_page_can_use_wider_board_source_than_final_sections(self):
        apple = self._item("apple")["short_label"]
        radish = self._item("radish")["short_label"]
        final_apple = self._make_article(
            "supply",
            f"{apple} 가격 강세와 출하 조절",
            f"{apple} 물량 감소로 가격 강세가 이어지고 있다.",
            "https://www.news1.kr/economy/food/999001",
        )
        board_radish = self._make_article(
            "supply",
            f"{radish} 가격 강세 지속",
            f"{radish} 수급 불안으로 도매가격이 오르고 있다.",
            "https://www.agrinet.co.kr/news/articleView.html?idxno=999002",
        )
        final_by_section = {key: [] for key in self.conf}
        final_by_section["supply"] = [final_apple]
        board_by_section = {key: [] for key in self.conf}
        board_by_section["supply"] = [final_apple, board_radish]
        html = main.render_daily_page(
            report_date="2026-03-15",
            start_kst=self.now,
            end_kst=self.now,
            by_section=final_by_section,
            archive_dates_desc=["2026-03-15"],
            site_path="https://example.com/agri-news-brief/",
            board_source_by_section=board_by_section,
        )
        self.assertIn(apple, html)
        self.assertIn(radish, html)


if __name__ == "__main__":
    unittest.main()
