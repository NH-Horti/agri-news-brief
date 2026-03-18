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

    def test_managed_commodity_group_order_places_fruit_veg_third(self):
        self.assertEqual(
            [str(group.get("key") or "") for group in main.MANAGED_COMMODITY_GROUP_SPECS],
            ["root_leaf", "seasoning_veg", "fruit_veg", "fruit_flower"],
        )

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

    def test_daily_pest_query_builder_includes_non_core_primary_items(self):
        queries = main.build_managed_pest_recall_queries(datetime(2026, 3, 15, tzinfo=main.KST))
        self.assertIn(main._managed_commodity_pest_queries(self._item("peach"))[0], queries)

    def test_managed_section_recall_queries_cover_supply_policy_and_dist(self):
        supply_queries = main.build_managed_section_recall_queries("supply", None)
        policy_queries = main.build_managed_section_recall_queries("policy", None)
        dist_queries = main.build_managed_section_recall_queries("dist", None)
        apple_supply = sum(main._managed_commodity_supply_query_buckets(self._item("apple")).values(), [])
        onion_supply = sum(main._managed_commodity_supply_query_buckets(self._item("onion")).values(), [])
        self.assertTrue(any(query in supply_queries for query in apple_supply))
        self.assertTrue(any(query in supply_queries for query in onion_supply))
        self.assertTrue(any(query in policy_queries for query in main._managed_commodity_policy_queries(self._item("apple"))))
        self.assertTrue(any(query in dist_queries for query in main._managed_commodity_dist_queries(self._item("apple"))))
        self.assertTrue(any(query in policy_queries for query in main._managed_commodity_policy_queries(self._item("cabbage"))))
        self.assertTrue(any(query in dist_queries for query in main._managed_commodity_dist_queries(self._item("cabbage"))))

    def test_daily_managed_recall_queries_cover_every_catalog_item(self):
        supply_queries = main.build_managed_section_recall_queries("supply", datetime(2026, 3, 13, tzinfo=main.KST))
        policy_queries = main.build_managed_section_recall_queries("policy", datetime(2026, 3, 13, tzinfo=main.KST))
        dist_queries = main.build_managed_section_recall_queries("dist", datetime(2026, 3, 13, tzinfo=main.KST))

        for item in main.MANAGED_COMMODITY_CATALOG:
            supply_buckets = main._managed_commodity_supply_query_buckets(item)
            self.assertTrue(any(query in supply_queries for query in sum(supply_buckets.values(), [])), item["key"])
            self.assertTrue(any(query in policy_queries for query in main._managed_commodity_policy_queries(item)), item["key"])
            self.assertTrue(any(query in dist_queries for query in main._managed_commodity_dist_queries(item)), item["key"])

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
        self.assertEqual(seasoning_group["inactive_count"], 5)
        self.assertNotIn("붉은고추", {item["label"] for group in ctx["groups"] for item in group["items"]})
        self.assertEqual(len(apple["preview_articles"]), 1)
        self.assertEqual(len(apple["secondary_articles"]), 0)
        self.assertEqual(len(apple["extra_articles"]), 0)
        self.assertGreaterEqual(float(apple["top_article_board_score"]), 0.0)

    def test_board_context_prefers_item_specific_top_article(self):
        item = self._item("apple")
        label = item["short_label"]
        generic_article = self._make_article(
            "supply",
            "원예 농산물 수급 점검 및 가격 동향",
            f"{label}와 배 등 과수 품목 전반의 가격과 수급 점검 내용을 다뤘다.",
            "https://example.com/apple-generic",
        )
        generic_article.score = 180.0
        specific_article = self._make_article(
            "dist",
            f"{label} 공동판매 확대와 출하 조절",
            f"{label} 산지 출하 조절과 공동판매 확대가 핵심으로 다뤄졌다.",
            "https://example.com/apple-specific",
        )
        specific_article.score = 55.0
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [generic_article]
        by_section["dist"] = [specific_article]
        ctx = main.build_managed_commodity_board_context(by_section)
        apple_item = next(payload for group in ctx["groups"] for payload in group["items"] if payload["key"] == "apple")
        self.assertEqual(apple_item["top_article"].title, specific_article.title)
        self.assertGreater(apple_item["top_article_board_score"], 0.0)

    def test_board_source_builder_keeps_managed_candidates_from_raw_pool(self):
        apple = self._item("apple")["short_label"]
        onion = self._item("onion")["short_label"]
        apple_article = self._make_article(
            "supply",
            f"{apple} 가격 강세와 출하 조절",
            f"{apple} 물량 감소로 가격 강세가 이어지고 있다.",
            "https://www.news1.kr/economy/food/999011",
        )
        onion_article = self._make_article(
            "dist",
            f"{onion} 소비 촉진과 공동판매 확대",
            f"{onion} 온라인 판매와 유통채널 다변화로 판로를 넓히고 있다.",
            "https://www.jibs.co.kr/news/replay/viewNewsReplayDetail/999011",
        )
        raw_by_section = {key: [] for key in self.conf}
        raw_by_section["supply"] = [apple_article]
        raw_by_section["dist"] = [onion_article]
        board_source = main.build_managed_commodity_board_source_by_section(raw_by_section, per_section_cap=12)
        ctx = main.build_managed_commodity_board_context(board_source)
        onion_item = next(item for group in ctx["groups"] for item in group["items"] if item["key"] == "onion")
        self.assertTrue(onion_item["active"])
        self.assertEqual(onion_item["article_count"], 1)
        self.assertEqual(onion_item["preview_articles"][0].title, onion_article.title)

    def test_managed_only_commodity_tags_are_emitted(self):
        radish = self._item("radish")["short_label"]
        green_onion = self._item("green_onion")["short_label"]
        tags = main._commodity_tags_in_text(f"{radish} 가격 급등과 {green_onion} 수급 불안이 이어진다.", limit=5)
        self.assertIn(radish, tags)
        self.assertIn(green_onion, tags)

    def test_program_core_supply_article_scores_above_generic_supply_peer(self):
        item = self._item("apple")
        label = item["short_label"]
        conf = self.conf["supply"]
        program_core_score = main.compute_rank_score(
            f"{label} 수급 불안에 가격 강세",
            f"{label} 출하 조절과 물량 감소로 가격 강세가 이어지고 있다.",
            "nongmin.com",
            self.now,
            conf,
            "농민신문",
        )
        generic_score = main.compute_rank_score(
            "과일 수급 불안에 가격 강세",
            "과일 출하 조절과 물량 감소로 가격 강세가 이어지고 있다.",
            "nongmin.com",
            self.now,
            conf,
            "농민신문",
        )
        self.assertGreater(program_core_score, generic_score)

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
        self.assertIn("전체 품목 보드", html)
        self.assertIn('data-view-tab="briefing"', html)
        self.assertIn('data-view-tab="commodity"', html)
        self.assertNotIn("secInsight", html)
        self.assertIn("오늘의 브리핑", html)
        self.assertIn("briefingHeroTitle", html)
        self.assertIn("commodityHeadStats", html)
        self.assertIn("commodityBoardNav", html)
        self.assertIn("syncStickyOffsets", html)
        self.assertIn("syncFloatingChipbar", html)
        self.assertIn("syncMobileQuickNav", html)
        self.assertIn('id="chipDock"', html)
        self.assertIn('id="mobileQuickNav"', html)
        self.assertIn("--group-chip-color", html)
        self.assertIn("--chip-color", html)
        self.assertIn("--chipbar-height", html)
        self.assertIn("--nav-chip-height", html)
        self.assertIn(label, html)
        self.assertIn("양념채소류", html)
        self.assertIn("활성 품목 0 / 5", html)
        self.assertIn("미연결 품목 5개", html)
        self.assertIn('data-swipe-ignore="1"', html)
        self.assertNotIn("붉은고추", html)
        self.assertLess(html.index("commodity-group-fruit_veg"), html.index("commodity-group-fruit_flower"))
        self.assertLess(html.index("briefingHeroTitle"), html.index('class="chipbar briefingChipbar"'))
        self.assertLess(html.index("commodityBoardTitle"), html.index('class="chipbar commodityBoardNav"'))
        self.assertIn(".chipDock{position:fixed;", html)
        self.assertIn(".commodityBoardNav{margin:18px 18px 20px}", html)
        self.assertIn(".chip,.commodityGroupChip{", html)
        self.assertIn(".chips,.commodityGroupNav{display:flex;gap:10px;align-items:center;justify-content:flex-start;width:100%;}", html)
        self.assertIn("@media (max-width: 900px) and (hover: none), (max-width: 900px) and (pointer: coarse){", html)
        self.assertIn(".viewTabEyebrow{display:none}", html)
        self.assertIn(".mobileQuickNavBody .chips,", html)
        self.assertIn("body.quickNavOpen{overflow:hidden}", html)
        self.assertIn("function isCompactViewport()", html)
        self.assertIn("window.innerWidth <= (coarsePointer ? 900 : 640)", html)
        self.assertIn("rect.top < dockTop && rect.bottom <= dockTop", html)
        self.assertIn('toggle: "품목군 이동"', html)
        self.assertIn('title: "품목군 바로가기"', html)
        self.assertIn('toggle: "섹션 이동"', html)
        self.assertIn('title: "섹션 바로가기"', html)

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

    def test_render_daily_page_shows_multiple_story_links_per_item(self):
        onion = self._item("onion")["short_label"]
        first = self._make_article(
            "dist",
            f"{onion} 소비 촉진과 공동판매 확대",
            f"{onion} 온라인 판매와 유통채널 다변화 기사다.",
            "https://example.com/onion-1",
        )
        second = self._make_article(
            "supply",
            f"{onion} 가격 하락에 소비 대책 시급",
            f"{onion} 산지 물량 부담으로 가격 하락세가 이어지고 있다.",
            "https://example.com/onion-2",
        )
        third = self._make_article(
            "policy",
            f"{onion} 수급 안정 협의체 출범",
            f"{onion} 수급 안정을 위한 협의체 운영 방안이 논의됐다.",
            "https://example.com/onion-3",
        )
        fourth = self._make_article(
            "pest",
            f"{onion} 생육 관리와 병해충 대응",
            f"{onion} 생육 리스크와 병해충 대응 현황을 짚었다.",
            "https://example.com/onion-4",
        )
        by_section = {key: [] for key in self.conf}
        board_by_section = {key: [] for key in self.conf}
        board_by_section["dist"] = [first]
        board_by_section["supply"] = [second]
        board_by_section["policy"] = [third]
        board_by_section["pest"] = [fourth]
        html = main.render_daily_page(
            report_date="2026-03-15",
            start_kst=self.now,
            end_kst=self.now,
            by_section=by_section,
            archive_dates_desc=["2026-03-15"],
            site_path="https://example.com/agri-news-brief/",
            board_source_by_section=board_by_section,
        )
        self.assertIn(first.title, html)
        self.assertIn(second.title, html)
        self.assertIn(third.title, html)
        self.assertIn(fourth.title, html)
        self.assertIn("commodityPrimaryStory", html)
        self.assertIn("commoditySupportList", html)
        self.assertIn("commodityMoreWrap", html)

    def test_render_debug_report_html_uses_page_scroll_friendly_table_styles(self):
        original_debug = main.DEBUG_REPORT
        original_write_json = main.DEBUG_REPORT_WRITE_JSON
        original_data = {
            "generated_at_kst": main.DEBUG_DATA.get("generated_at_kst"),
            "build_tag": main.DEBUG_DATA.get("build_tag"),
            "filter_rejects": list(main.DEBUG_DATA.get("filter_rejects", [])),
            "sections": dict(main.DEBUG_DATA.get("sections", {})),
        }
        try:
            main.DEBUG_REPORT = True
            main.DEBUG_REPORT_WRITE_JSON = False
            main.DEBUG_DATA["generated_at_kst"] = "2026-03-15T09:00:00+09:00"
            main.DEBUG_DATA["build_tag"] = "test-build"
            main.DEBUG_DATA["filter_rejects"] = []
            main.DEBUG_DATA["sections"] = {}
            html = main.render_debug_report_html("2026-03-15", "https://example.com/agri-news-brief/")
        finally:
            main.DEBUG_REPORT = original_debug
            main.DEBUG_REPORT_WRITE_JSON = original_write_json
            main.DEBUG_DATA["generated_at_kst"] = original_data["generated_at_kst"]
            main.DEBUG_DATA["build_tag"] = original_data["build_tag"]
            main.DEBUG_DATA["filter_rejects"] = original_data["filter_rejects"]
            main.DEBUG_DATA["sections"] = original_data["sections"]
        self.assertIn("overflow-x:auto", html)
        self.assertIn("overflow-y:visible", html)
        self.assertNotIn("position:sticky", html)


if __name__ == "__main__":
    unittest.main()
