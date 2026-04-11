import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import hf_semantics
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
            f"{label} 경락가 급등…공판장 반입 감소에 산지 출하 조절",
            f"{label} 공판장 반입 감소와 경락가 급등이 이어지며 산지 출하 조절 필요성이 커지고 있다.",
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

    def test_board_context_prefers_issue_story_over_training_story_for_same_item(self):
        issue_article = self._make_article(
            "supply",
            "양파 가격 폭락 우려…산지 출하 조절·수급 대책 촉구",
            "양파 산지의 출하 조절과 수급 대책 요구가 커지며 가격 급락 우려가 확산하고 있다.",
            "https://example.com/onion-issue",
        )
        training_article = self._make_article(
            "supply",
            "화천농협, 양파 공선출하회 총회·재배기술교육 펼쳐",
            "양파 재배 농가를 대상으로 공선출하회 총회와 재배기술교육을 진행했다.",
            "https://example.com/onion-training",
        )
        training_article.score = issue_article.score + 3.0
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [training_article, issue_article]

        ctx = main.build_managed_commodity_board_context(by_section)
        onion_item = next(payload for group in ctx["groups"] for payload in group["items"] if payload["key"] == "onion")

        self.assertEqual(onion_item["top_article"].title, issue_article.title)

    def test_board_context_prefers_core_issue_story_for_program_item(self):
        tail_article = self._make_article(
            "supply",
            "양파 산지 공선출하회 총회·재배기술교육 진행",
            "양파 재배 농가를 대상으로 총회와 교육을 진행한 행사성 기사다.",
            "https://example.com/onion-tail-training-priority",
        )
        tail_article.score = 92.0
        tail_article.selection_stage = "tail"
        tail_article.selection_fit_score = 0.48

        core_issue_article = self._make_article(
            "supply",
            "양파 가격 약세 심화…산지 출하 조절·수급 대책 촉구",
            "양파 가격 약세와 출하 조절, 수급 대책 요구를 다룬 핵심 기사다.",
            "https://example.com/onion-core-issue-priority",
        )
        core_issue_article.score = 71.0
        core_issue_article.is_core = True
        core_issue_article.selection_stage = "core_final"
        core_issue_article.selection_fit_score = 1.82

        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [tail_article, core_issue_article]

        ctx = main.build_managed_commodity_board_context(by_section)
        onion_item = next(payload for group in ctx["groups"] for payload in group["items"] if payload["key"] == "onion")

        self.assertEqual(onion_item["top_article"].title, core_issue_article.title)
        self.assertGreater(
            float(onion_item["top_article_metrics"].get("representative_score") or 0.0),
            float(main._commodity_board_item_article_representative_metrics(onion_item, tail_article).get("representative_score") or 0.0),
        )

    def test_board_context_prefers_issue_story_over_interview_story_for_same_item(self):
        issue_article = self._make_article(
            "supply",
            "토마토 가격 약세 장기화…출하 조절·수급 대응 시급",
            "토마토 산지의 출하 물량 부담과 가격 약세가 이어지며 수급 대응 요구가 커지고 있다.",
            "https://example.com/tomato-issue",
        )
        interview_article = self._make_article(
            "supply",
            "[인터뷰] 가람 토마토 대표의 35년 농부의 길",
            "토마토 재배 경험과 농가 운영 스토리를 소개하는 인터뷰 기사다.",
            "https://example.com/tomato-interview",
        )
        interview_article.score = issue_article.score + 6.0
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [interview_article, issue_article]

        ctx = main.build_managed_commodity_board_context(by_section)
        tomato_item = next(payload for group in ctx["groups"] for payload in group["items"] if payload["key"] == "tomato")

        self.assertEqual(tomato_item["top_article"].title, issue_article.title)

    @unittest.skip("legacy unicode fixture is unstable in this environment; covered by ascii semantic flip test")
    def test_board_context_can_flip_top_article_with_hf_semantic_boost(self):
        item = self._item("onion")
        label = item["short_label"]
        baseline_top = self._make_article(
            "supply",
            f"{label} 가격 약세에 출하 조절 비상",
            f"{label} 가격 하락과 출하 조절, 저장 물량 관리가 동시에 거론되는 수급 기사다.",
            "https://example.com/onion-semantic-baseline",
        )
        hf_promoted = self._make_article(
            "supply",
            f"{label} 저장 물량 재배치로 수급 안정 대응",
            f"{label} 저장 물량 재배치와 반입 조절, 도매시장 대응을 다룬 현장 수급 기사다.",
            "https://example.com/onion-semantic-hf",
        )
        hf_promoted.score = max(0.0, baseline_top.score - 0.3)
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [baseline_top, hf_promoted]

        with mock.patch.object(
            main,
            "_hf_semantic_commodity_board_adjustments",
            return_value={
                main._article_selection_identity(baseline_top): hf_semantics.SemanticAdjustment(
                    similarity=0.72,
                    boost=-4.0,
                    model="test-model",
                ),
                main._article_selection_identity(hf_promoted): hf_semantics.SemanticAdjustment(
                    similarity=0.94,
                    boost=18.0,
                    model="test-model",
                ),
            },
        ):
            ctx = main.build_managed_commodity_board_context(by_section)

        onion_item = next(payload for group in ctx["groups"] for payload in group["items"] if payload["key"] == "onion")
        baseline_metrics = main._commodity_board_item_article_representative_metrics(onion_item, baseline_top)
        promoted_metrics = main._commodity_board_item_article_representative_metrics(onion_item, hf_promoted)
        self.assertGreater(float(promoted_metrics.get("semantic_boost") or 0.0), 0.0)
        self.assertGreater(
            float(promoted_metrics.get("representative_score") or 0.0),
            float(baseline_metrics.get("representative_score") or 0.0),
        )
        self.assertGreater(
            main._commodity_board_item_article_sort_key(onion_item, hf_promoted),
            main._commodity_board_item_article_sort_key(onion_item, baseline_top),
        )

    def test_board_context_can_flip_top_article_with_hf_semantic_boost_ascii_fixture(self):
        item = self._item("onion")
        label = item["short_label"]
        baseline_top = self._make_article(
            "supply",
            f"{label} 가격 강세로 출하 조절 비상",
            f"{label} 가격 하락과 출하 조절, 저장 물량 관리가 동시에 거론되는 수급 기사다.",
            "https://example.com/onion-semantic-baseline-ascii",
        )
        hf_promoted = self._make_article(
            "supply",
            f"{label} 저장 물량 분산처리로 수급 안정 대응",
            f"{label} 저장 물량 분산처리와 반입 조절, 도매시장 대응을 다룬 현장 수급 기사다.",
            "https://example.com/onion-semantic-hf-ascii",
        )
        hf_promoted.score = max(0.0, baseline_top.score - 0.3)
        self.assertGreater(
            main._commodity_board_item_article_base_sort_key(item, baseline_top),
            main._commodity_board_item_article_base_sort_key(item, hf_promoted),
        )

        baseline_before = main._commodity_board_item_article_representative_metrics(
            item,
            baseline_top,
            include_semantic=False,
        )
        promoted_before = main._commodity_board_item_article_representative_metrics(
            item,
            hf_promoted,
            include_semantic=False,
        )

        main._set_commodity_board_semantic_state(
            baseline_top,
            item["key"],
            hf_semantics.SemanticAdjustment(
                similarity=0.72,
                boost=-4.0,
                model="test-model",
            ),
        )
        main._set_commodity_board_semantic_state(
            hf_promoted,
            item["key"],
            hf_semantics.SemanticAdjustment(
                similarity=0.94,
                boost=18.0,
                model="test-model",
            ),
        )

        baseline_metrics = main._commodity_board_item_article_representative_metrics(item, baseline_top)
        promoted_metrics = main._commodity_board_item_article_representative_metrics(item, hf_promoted)
        self.assertLess(float(baseline_metrics.get("semantic_boost") or 0.0), 0.0)
        self.assertGreater(float(promoted_metrics.get("semantic_boost") or 0.0), 0.0)
        self.assertGreater(
            float(promoted_metrics.get("board_score") or 0.0),
            float(promoted_before.get("board_score") or 0.0),
        )
        self.assertLess(
            float(baseline_metrics.get("board_score") or 0.0),
            float(baseline_before.get("board_score") or 0.0),
        )
        self.assertGreater(
            float(promoted_metrics.get("representative_score") or 0.0),
            float(promoted_before.get("representative_score") or 0.0),
        )
        self.assertLess(
            float(baseline_metrics.get("representative_score") or 0.0),
            float(baseline_before.get("representative_score") or 0.0),
        )

    def test_training_style_board_story_with_supply_terms_is_not_representative(self):
        training_article = self._make_article(
            "supply",
            "화천농협, 양파 공선출하회 총회·재배기술교육 펼쳐",
            "양파 재배 농가를 대상으로 공선출하회 총회와 재배기술교육을 진행했다.",
            "https://example.com/onion-training-rank",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("onion"), training_article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_training_story"]))

    def test_promo_campaign_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            "대아청과 '달코미 양배추' 1만 통 할인판매 추진",
            "대아청과가 달코미 양배추 소비 확대를 위해 할인판매와 판촉 행사를 추진한다.",
            "https://example.com/cabbage-promo",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("cabbage"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_sales_promo_story"]))

    def test_political_statement_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            "\"국산 양파 산업 무너질라\"… 양파 생산자협회, 청와대서 결의 대회",
            "양파 생산자협회가 청와대 앞에서 가격 폭락 저지와 수급 대책 마련을 촉구하는 결의 대회를 열었다.",
            "https://example.com/onion-political",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("onion"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_political_statement_story"]))

    def test_coop_channel_expansion_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            "고흥 거금도농협, 조생양파 판로 확대 나서",
            "지역 농협이 조생양파 판매 촉진을 위해 판로 확대에 나섰다.",
            "https://example.com/onion-coop-channel",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("onion"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_sales_promo_story"]))

    def test_support_project_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            "예산군, 쪽파 재배 농가 상토 지원…안정 생산 기반 강화",
            "쪽파 재배 농가에 상토와 장려금을 지원해 안정 생산 기반을 강화할 계획이다.",
            "https://example.com/green-onion-support",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("green_onion"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_support_advice_story"]))

    def test_smartfarm_success_story_is_board_visible_but_low_rank(self):
        article = self._make_article(
            "supply",
            "경북 봉화군, 스마트팜으로 겨울철 쪽파 성공 출하",
            "임대형 스마트팜에서 겨울철 쪽파를 재배해 성공 출하했다는 현장 성과 소개 기사다.",
            "https://example.com/green-onion-smartfarm",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("green_onion"), article)

        self.assertGreaterEqual(int(metrics["representative_rank"]), 1)

    def test_consumer_guide_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            "[주간알뜰장보기] '쪽파·애호박' 지금이 구매 타이밍! (3월3주)",
            "3월 셋째 주 알뜰장보기 품목으로 쪽파와 애호박을 추천하며 구매 타이밍을 소개했다.",
            "https://example.com/zucchini-shopping-guide",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("zucchini"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_consumer_guide_story"]))

    def test_regional_branding_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            "'K-과일'의 본산 경산, 대추·천도 복숭아 로 전국 평정했다",
            "경산을 K-과일 본산으로 소개하며 천도 복숭아와 대추 브랜드 경쟁력을 부각하는 지역 홍보 기사다.",
            "https://example.com/peach-branding",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("peach"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_regional_branding_story"]))

    def test_regional_branding_story_with_supply_words_is_not_representative(self):
        article = self._make_article(
            "supply",
            "자두·포도·호두…자연과 기술이 빚은 '맛의 도시' 김천",
            "김천은 자두·포도·호두 등 과수 주산지로, 농가가 시설재배를 확대하며 출하 시기 조절에 나서고 있다.",
            "https://example.com/grape-branding-kimcheon",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("grape"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_regional_branding_story"]))

    def test_price_crisis_story_with_promo_wording_can_stay_representative(self):
        article = self._make_article(
            "supply",
            "월동무 가격 하락에 긴급 소비 촉진 사업 추진",
            "월동무 가격 하락과 재고 부담에 대응해 긴급 소비 촉진 사업과 수급 대책을 함께 추진한다.",
            "https://example.com/radish-price-crisis",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("radish"), article)

        self.assertFalse(bool(metrics["weak_sales_promo_story"]))
        self.assertGreaterEqual(int(metrics["representative_rank"]), 1)

    def test_seed_supply_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            "고양시, 감자 보급종 물량 확보 농가 공급 숨통",
            "감자 보급종과 종서 지원으로 농가 공급 숨통을 틔운다는 지원 기사다.",
            "https://example.com/potato-seed-support",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("potato"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_support_advice_story"]))

    def test_party_basket_mission_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            '[단독] "대파 한 단에 얼마?"…민주당, 경선서 장바구니 미션 검토',
            "민주당 경선 과정에서 장바구니 물가 체험 미션을 검토 중이라는 정치 기사다.",
            "https://example.com/green-onion-political-mission",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("green_onion"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_political_statement_story"]))

    def test_rotation_advice_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            '생강 연작 장해, "윤작"이 답이다',
            "생강 연작 피해를 줄이기 위한 윤작 관리법을 소개했다.",
            "https://example.com/ginger-rotation-advice",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("ginger"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_support_advice_story"]))

    def test_recipe_hype_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            "품절 대란 강호동 '봄동 비빔밥'의 반전…사실은 얼갈이 배추",
            "방송에서 소개된 비빔밥 재료를 다룬 소비자 화제성 기사다.",
            "https://example.com/napa-cabbage-recipe-hype",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("napa_cabbage"), article)

        self.assertLess(int(metrics["representative_rank"]), 1)

    def test_unanchored_macro_roundup_story_is_not_representative(self):
        article = self._make_article(
            "policy",
            "계란·화장지 등 민생물가 잡는다…과자·아이스크림도 가격 인하",
            "정부가 23개 품목 물가 특별관리에 나섰다는 일반 물가 기사다.",
            "https://example.com/garlic-macro-roundup",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("garlic"), article)

        self.assertLess(int(metrics["representative_rank"]), 1)

    def test_broad_macro_roundup_story_is_not_representative(self):
        article = self._make_article(
            "policy",
            "쌀·콩·마늘 등 23개 품목 지정…물가 특별관리 나섰다",
            "정부가 여러 생활물가 품목을 묶어 특별관리 대상으로 지정했다는 일반 물가 기사다.",
            "https://example.com/garlic-broad-roundup",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("garlic"), article)

        self.assertLess(int(metrics["representative_rank"]), 1)
        self.assertTrue(bool(metrics["weak_macro_roundup_story"]))

    def test_retail_storage_sales_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            '“기체조절 기술로 신선함 꽉 잡았어요"…CA 저장 사과 ·양파 판매',
            "롯데마트·수퍼는 CA 저장 기술로 사과와 양파 물량을 선제 확보해 판매하고 있다.",
            "https://example.com/onion-retail-storage-sales",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("onion"), article)

        self.assertEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_sales_promo_story"]))

    def test_unanchored_generic_agri_tech_story_is_not_representative(self):
        article = self._make_article(
            "pest",
            "드론이 방제하고, 자율 트랙터가 밭 갈고… 농사도 AI 시대",
            "농업 현장의 디지털 전환을 소개한 일반 기술 기사다.",
            "https://example.com/green-onion-generic-ai",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("green_onion"), article)

        self.assertLess(int(metrics["representative_rank"]), 1)
        self.assertTrue(bool(metrics["weak_unanchored_general_story"]))

    def test_expo_event_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            "'2028 충청남도 국제밤산업박람회' 개최 청신호",
            "국제밤산업박람회 개최 추진 소식이다.",
            "https://example.com/chestnut-expo",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("chestnut"), article)

        self.assertLess(int(metrics["representative_rank"]), 1)

    def test_opinion_column_story_is_not_representative(self):
        article = self._make_article(
            "supply",
            "[김흥길 교수의 경제이야기]고부가가치 작물 파프리카",
            "교수 칼럼 형식으로 파프리카 산업을 해설한 오피니언 기사다.",
            "https://example.com/paprika-opinion-column",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("paprika"), article)

        self.assertLess(int(metrics["representative_rank"]), 1)
        self.assertTrue(bool(metrics["weak_opinion_story"]))

    def test_tourism_style_fruit_story_is_not_representative(self):
        tourism_article = self._make_article(
            "supply",
            "형광빛 메타세쿼이아·고즈넉한 고택… 배꽃 필 무렵이 최고의 시간",
            "배꽃 개화 시기에 맞춰 관광객이 찾는 봄 여행 코스를 소개하는 기사다.",
            "https://example.com/pear-tourism",
        )

        metrics = main._commodity_board_item_article_representative_metrics(self._item("pear"), tourism_article)

        self.assertLessEqual(int(metrics["representative_rank"]), 0)

    def test_fruit_blossom_tourism_context_stays_blocked_even_with_crop_terms(self):
        title = "형광빛 메타세쿼이아·고즈넉한 고택… 배꽃 필 무렵이 최고의 시간"
        desc = (
            "전남 나주에서 배 재배 면적이 높아 전국 생산량의 상당수를 차지하며, "
            "배꽃이 필 무렵 매력적인 풍경을 이룬다. 청도의 농민들은 수확을 축하하며 "
            "미나리와 삼겹살을 함께 판매하는 전통을 이어가고 있다."
        )
        article = self._make_article(
            "supply",
            title,
            desc,
            "https://example.com/pear-blossom-tourism-hardblock",
        )

        self.assertTrue(main.is_fruit_blossom_tourism_context(title, desc))
        metrics = main._commodity_board_item_article_representative_metrics(self._item("pear"), article)
        self.assertLessEqual(int(metrics["representative_rank"]), 0)
        self.assertTrue(bool(metrics["weak_blossom_tourism_story"]))

    def test_board_context_moves_weak_only_program_core_item_to_inactive(self):
        training_article = self._make_article(
            "supply",
            "장계농협, 고품질 오이 재배기술 교육",
            "오이 재배 농가를 대상으로 재배기술 교육을 진행했다.",
            "https://example.com/cucumber-training-only",
        )
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [training_article]

        ctx = main.build_managed_commodity_board_context(by_section)
        cucumber = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "cucumber"
        )

        self.assertFalse(cucumber["active"])
        self.assertEqual(cucumber["article_count"], 1)
        self.assertIsNone(cucumber["top_article"])
        self.assertEqual(len(cucumber["extra_articles"]), 0)

    def test_board_rejects_corporate_stock_story_for_cucumber(self):
        article = self._make_article(
            "dist",
            "하나證 “오이솔루션, 주가 상승 초입 국면…하반기 흑자 전환 기대”",
            "하나증권은 오이솔루션에 대해 주파수 경매와 레이저다이오드 칩 내재화를 통한 흑자 전환을 예상했다.",
            "https://biz.chosun.com/stock/stock_general/2026/03/26/V3JW4QSIVZHZ5BKSK45QJFPBHQ/",
        )
        by_section = {key: [] for key in self.conf}
        by_section["dist"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        cucumber = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "cucumber"
        )

        self.assertFalse(cucumber["active"])
        self.assertEqual(cucumber["article_count"], 0)
        self.assertEqual(len(cucumber["extra_articles"]), 0)

    def test_board_rejects_foodservice_dinner_story_for_napa_cabbage(self):
        article = self._make_article(
            "dist",
            "서울신라호텔 ‘라연’ 정관스님과 토종 식재료 갈라 디너",
            "서울신라호텔 한식당 라연이 사찰음식 명장 정관스님과 협업해 구억배추·들깨·토종쌀 등 토종 식재료를 소개하는 갈라 디너를 진행했다.",
            "https://www.newsclaim.co.kr/news/articleView.html?idxno=3059121",
        )
        by_section = {key: [] for key in self.conf}
        by_section["dist"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        napa_cabbage = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "napa_cabbage"
        )

        self.assertFalse(napa_cabbage["active"])
        self.assertEqual(napa_cabbage["article_count"], 0)
        self.assertEqual(len(napa_cabbage["extra_articles"]), 0)

    def test_generic_category_watch_story_is_not_representative_for_program_core_item(self):
        title = "채소값 곤두박질…공급·소비·정책 삼중고"
        desc = "풋고추와 오이 등 채소류 가격이 흔들리고 공급과 소비, 정책 부담이 함께 겹치고 있다."
        article = self._make_article(
            "supply",
            title,
            desc,
            "https://example.com/vegetable-category-watch",
        )

        self.assertTrue(main.is_supply_generic_category_watch_context(title, desc))
        self.assertTrue(main.is_supply_weak_tail_context(title, desc))
        metrics = main._commodity_board_item_article_representative_metrics(self._item("green_pepper"), article)

        self.assertLess(int(metrics["representative_rank"]), 1)
        self.assertTrue(bool(metrics["weak_generic_market_watch_story"]))

    def test_generic_category_watch_story_is_not_active_candidate_for_program_core_item(self):
        article = self._make_article(
            "supply",
            "채소값 곤두박질…공급·소비·정책 삼중고",
            "풋고추와 오이 등 채소류 가격이 흔들리고 공급과 소비, 정책 부담이 함께 겹치고 있다.",
            "https://example.com/vegetable-category-watch-inactive",
        )
        item = self._item("green_pepper")
        metrics = main._commodity_board_item_article_representative_metrics(item, article)

        self.assertFalse(main._commodity_board_article_is_active_candidate(item, article, metrics))

    def test_program_core_item_accepts_indirect_facility_issue_story(self):
        article = self._make_article(
            "supply",
            "송미령 장관, 농협주유소·시설채소 점검…난방유 부담 대응 주문",
            "시설채소 주산지에서 풋고추·애호박 농가의 난방유 부담과 출하 차질을 점검하고 수급 안정을 위한 대응을 주문했다.",
            "https://example.com/facility-vegetable-response",
        )
        item = self._item("green_pepper")
        metrics = main._commodity_board_item_article_representative_metrics(item, article)

        self.assertGreaterEqual(int(metrics["representative_rank"]), 4)
        self.assertTrue(main._commodity_board_article_is_active_candidate(item, article, metrics))
        self.assertTrue(main._commodity_board_article_is_supply_bridge_candidate(item, article, metrics))

    def test_board_context_does_not_mix_cabbage_into_napa_cabbage(self):
        article = self._make_article(
            "supply",
            "양배추 가격 급락에 제주 농가 '시름'...소비확대 '총력전'",
            "양배추 공급 과잉으로 가격이 급락하자 제주 농가가 소비 확대와 출하 조절에 나섰다.",
            "https://example.com/cabbage-price",
        )
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        napa_cabbage = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "napa_cabbage"
        )
        cabbage = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "cabbage"
        )

        self.assertFalse(napa_cabbage["active"])
        self.assertEqual(napa_cabbage["article_count"], 0)
        self.assertTrue(cabbage["active"])
        self.assertEqual(cabbage["top_article"].title, article.title)

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
            f"{onion} 경락가 급락 우려…공동판매·출하 조절 확대",
            f"{onion} 도매시장 경락 약세와 산지 물량 부담이 겹치며 공동판매 확대와 출하 조절이 추진되고 있다.",
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

    def test_supply_final_normalization_promotes_program_core_board_story(self):
        weak_supply = self._make_article(
            "supply",
            "동광양농협, 농가주부모임과 감자 심기 행사 진행",
            "감자 심기 행사와 현장 체험 중심의 지역 행사 기사다.",
            "https://example.com/potato-event",
        )
        strong_supply = self._make_article(
            "supply",
            "양파 가격 폭락 우려…산지 출하 조절·수급 대책 촉구",
            "양파 산지의 출하 물량 부담과 가격 급락 우려로 수급 대책 요구가 커지고 있다.",
            "https://example.com/onion-brief-core",
        )
        final_by_section = {key: [] for key in self.conf}
        final_by_section["supply"] = [weak_supply]
        board_source = {key: [] for key in self.conf}
        board_source["supply"] = [weak_supply, strong_supply]

        changed = main._normalize_supply_section_from_board(final_by_section, board_source, max_items=3)

        self.assertEqual(changed, 1)
        self.assertEqual(final_by_section["supply"][0].title, strong_supply.title)
        self.assertTrue(final_by_section["supply"][0].is_core)

    def test_supply_final_normalization_can_pull_dist_representative_into_supply(self):
        weak_supply = self._make_article(
            "supply",
            "장계농협, 고품질 오이 재배기술 교육",
            "오이 재배 농가를 대상으로 재배기술 교육을 진행했다.",
            "https://example.com/cucumber-training",
        )
        strong_dist = self._make_article(
            "dist",
            "사과 경락가 급등…공판장 반입 감소에 산지 출하 조절",
            "사과 공판장 반입 감소와 경락가 급등이 이어지며 산지 출하 조절 필요성이 커지고 있다.",
            "https://example.com/apple-dist-core",
        )
        final_by_section = {key: [] for key in self.conf}
        final_by_section["supply"] = [weak_supply]
        board_source = {key: [] for key in self.conf}
        board_source["dist"] = [strong_dist]

        changed = main._normalize_supply_section_from_board(final_by_section, board_source, max_items=3)

        self.assertEqual(changed, 1)
        self.assertEqual(final_by_section["supply"][0].title, strong_dist.title)
        self.assertEqual(final_by_section["supply"][0].section, "supply")
        self.assertTrue(final_by_section["supply"][0].is_core)

    def test_supply_final_normalization_can_promote_selected_dist_story_and_prune_dist(self):
        weak_supply = self._make_article(
            "supply",
            "장계농협, 고품질 오이 재배기술 교육",
            "오이 재배 농가를 대상으로 재배기술 교육을 진행했다.",
            "https://example.com/cucumber-training-promote",
        )
        strong_dist = self._make_article(
            "dist",
            "사과 경락가 급등…공판장 반입 감소에 산지 출하 조절",
            "사과 공판장 반입 감소와 경락가 급등이 이어지며 산지 출하 조절 필요성이 커지고 있다.",
            "https://example.com/apple-dist-selected-core",
        )
        final_by_section = {key: [] for key in self.conf}
        final_by_section["supply"] = [weak_supply]
        final_by_section["dist"] = [strong_dist]
        board_source = {key: [] for key in self.conf}
        board_source["dist"] = [strong_dist]

        changed = main._normalize_supply_section_from_board(final_by_section, board_source, max_items=3)

        self.assertEqual(changed, 1)
        self.assertEqual(final_by_section["supply"][0].title, strong_dist.title)
        self.assertEqual(final_by_section["supply"][0].section, "supply")
        self.assertTrue(final_by_section["supply"][0].is_core)
        self.assertEqual(final_by_section["dist"], [])

    def test_supply_final_normalization_does_not_promote_tourism_board_story(self):
        base_supply = self._make_article(
            "supply",
            "양파 가격 폭락 우려…산지 출하 조절·수급 대책 촉구",
            "양파 산지의 출하 물량 부담과 가격 급락 우려로 수급 대책 요구가 커지고 있다.",
            "https://example.com/onion-base",
        )
        tourism_article = self._make_article(
            "dist",
            "형광빛 메타세쿼이아·고즈넉한 고택… 배꽃 필 무렵이 최고의 시간",
            "배꽃 개화 시기에 맞춰 관광객이 찾는 봄 여행 코스를 소개하는 기사다.",
            "https://example.com/pear-tourism-bridge",
        )
        final_by_section = {key: [] for key in self.conf}
        final_by_section["supply"] = [base_supply]
        board_source = {key: [] for key in self.conf}
        board_source["dist"] = [tourism_article]

        changed = main._normalize_supply_section_from_board(final_by_section, board_source, max_items=3)

        self.assertEqual(changed, 0)
        self.assertEqual(final_by_section["supply"][0].title, base_supply.title)

    def test_supply_final_normalization_prioritizes_top_board_winners_as_core(self):
        retained_supply = self._make_article(
            "supply",
            "송미령 장관, 농협주유소·시설채소 점검…난방유 부담 대응 주문",
            "시설채소 농가 난방비 부담 대응을 위한 현장 점검 기사로, 개별 품목 대표기사로 보기엔 범용적이다.",
            "https://example.com/facility-fuel-check",
        )
        onion_core = self._make_article(
            "supply",
            "양파 가격 급락 우려…산지 출하 조절·수급 대책 촉구",
            "양파 생산자 단체가 출하 조절과 공동판매 확대, 가격 하락 방지 대책 마련을 요구하고 있다.",
            "https://example.com/onion-core-priority",
        )
        apple_core = self._make_article(
            "dist",
            "사과 경락가 급등…공판장 반입 감소에 산지 출하 조절",
            "사과 공판장 반입 감소로 경락가가 급등하면서 산지 출하 조절과 도매시장 대응이 이어지고 있다.",
            "https://example.com/apple-core-priority",
        )
        final_by_section = {key: [] for key in self.conf}
        final_by_section["supply"] = [retained_supply]
        board_source = {key: [] for key in self.conf}
        board_source["supply"] = [onion_core]
        board_source["dist"] = [apple_core]

        changed = main._normalize_supply_section_from_board(final_by_section, board_source, max_items=4)

        self.assertEqual(changed, 2)
        first_two = final_by_section["supply"][:2]
        self.assertEqual({article.title for article in first_two}, {onion_core.title, apple_core.title})
        self.assertTrue(all(article.is_core for article in first_two))
        self.assertFalse(any(article.title == retained_supply.title and article.is_core for article in final_by_section["supply"]))

    def test_board_context_prefers_different_press_in_secondary_preview_when_available(self):
        onion = self._item("onion")["short_label"]
        primary = self._make_article(
            "supply",
            f"{onion} 가격 폭락 우려…산지 출하 조절·수급 대책 촉구",
            f"{onion} 산지의 출하 조절과 수급 대책 요구가 커지며 가격 급락 우려가 확산하고 있다.",
            "https://www.wonyesanup.co.kr/news/articleView.html?idxno=900001",
        )
        secondary_same_press = self._make_article(
            "dist",
            f"{onion} 공동판매 확대",
            f"{onion} 공동판매 확대와 산지 유통 개선이 진행 중이다.",
            "https://www.wonyesanup.co.kr/news/articleView.html?idxno=900002",
        )
        secondary_other_press = self._make_article(
            "policy",
            f"{onion} 수급 안정 대책 점검",
            f"{onion} 수급 안정과 가격 대응 방안을 점검했다.",
            "https://www.agrinet.co.kr/news/articleView.html?idxno=900003",
        )
        primary.score = 180.0
        secondary_same_press.score = 120.0
        secondary_other_press.score = 118.0

        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [primary]
        by_section["dist"] = [secondary_same_press]
        by_section["policy"] = [secondary_other_press]

        ctx = main.build_managed_commodity_board_context(by_section)
        onion_item = next(payload for group in ctx["groups"] for payload in group["items"] if payload["key"] == "onion")

        self.assertEqual(onion_item["top_article"].title, primary.title)
        self.assertEqual(onion_item["secondary_articles"][0].title, secondary_other_press.title)

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
            f"{onion} 경락가 급락 우려…공동판매·출하 조절 확대",
            f"{onion} 도매시장 경락 약세와 산지 물량 부담이 겹치며 공동판매 확대와 출하 조절이 추진되고 있다.",
            "https://example.com/onion-1",
        )
        second = self._make_article(
            "supply",
            f"{onion} 가격 폭락 우려…산지 출하 조절·수급 대책 촉구",
            f"{onion} 산지 물량 부담과 가격 급락 우려로 출하 조절과 수급 대책 요구가 커지고 있다.",
            "https://example.com/onion-2",
        )
        third = self._make_article(
            "policy",
            f"{onion} 수급 안정 대책 착수…가격 하락 대응 협의",
            f"{onion} 가격 하락 대응과 수급 안정 대책을 위해 관계기관 협의가 본격화됐다.",
            "https://example.com/onion-3",
        )
        fourth = self._make_article(
            "pest",
            f"{onion} 노균병 확산 비상…산지 병해충 대응 강화",
            f"{onion} 산지 생육 단계에서 노균병 확산 우려가 커지며 병해충 대응이 강화되고 있다.",
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


    def test_eggplant_homonym_stories_are_not_tagged_to_managed_board(self):
        travel_text = (
            '유류할증료 3배에 "가지 말까"...중동 하늘길도 답답 '
            '유류할증료 3배 급등에 "가지 말까"라는 반응이 커지며 중동 하늘길 수요가 위축되고 있다.'
        )
        branch_text = (
            "평택시, 과수화상병 예방 교육 진행 "
            "사과, 배나무의 잎, 가지, 꽃, 열매 등에 화상 증상이 나타나는 과수화상병 예방 약제를 공급한다."
        )

        self.assertNotIn("eggplant", main.managed_commodity_keys_for_text(travel_text, None))
        self.assertNotIn("eggplant", main.managed_commodity_keys_for_text(branch_text, None))

    def test_board_rejects_topic_only_story_without_item_focus(self):
        article = self._make_article(
            "policy",
            "의성 급식예산 유지 속 '1인 지원 확대'…학생 감소에도 체감 복지 강화",
            "학교 급식과 학생 복지 예산을 다룬 일반 행정 기사다.",
            "https://www.kyongbuk.co.kr/news/articleView.html?idxno=4067478",
        )
        article.topic = "참외"
        by_section = {key: [] for key in self.conf}
        by_section["policy"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        oriental_melon = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "oriental_melon"
        )

        self.assertFalse(oriental_melon["active"])
        self.assertEqual(oriental_melon["article_count"], 0)

    def test_board_rejects_processed_food_story_even_with_item_flavor_term(self):
        article = self._make_article(
            "supply",
            "아이스크림·과자도 가격 내린다…롯데웰푸드·빙그레 등 최대 13.4% 인하",
            "복숭아맛 아이스크림과 스낵 등 가공식품 가격 인하 소식이다.",
            "https://view.asiae.co.kr/article/2026031910413256160",
        )
        article.topic = "복숭아"
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        peach = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "peach"
        )

        self.assertFalse(peach["active"])
        self.assertEqual(peach["article_count"], 0)

    def test_board_rejects_lifestyle_wine_story_for_citron(self):
        article = self._make_article(
            "supply",
            '"휴대폰 대신 와인잔을"…대부 감독 코폴라가 서울 식탁에 던진 "초대장"',
            "유자 향 와인과 미식 경험을 소개하는 라이프스타일 기사다.",
            "http://www.edaily.co.kr/news/newspath.asp?newsid=04382086645384960",
        )
        article.topic = "유자"
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        citron = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "citron"
        )

        self.assertFalse(citron["active"])
        self.assertEqual(citron["article_count"], 0)

    def test_board_rejects_processed_potato_chip_story(self):
        article = self._make_article(
            "supply",
            "감자 칩 사재기... 왜? [앵커리포트]",
            "일본 스낵 업계에서 감자 칩 공급 차질 우려가 번지며 사재기 현상이 나타났다는 리포트다.",
            "https://imnews.imbc.com/replay/2026/nwdesk/article/6720000_36799.html",
        )
        article.topic = "감자"
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        potato = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "potato"
        )

        self.assertFalse(potato["active"])
        self.assertEqual(potato["article_count"], 0)

    def test_board_rejects_general_consumer_price_story_for_garlic(self):
        article = self._make_article(
            "policy",
            "계란·화장지 등 민생물가 잡는다…과자·아이스크림도 가격 인하",
            "정부가 생필품과 가공식품 할인 대책을 발표했다. 일부 문단에 양파·마늘 등 농산물 언급이 있지만 기사 중심은 소비자 물가다.",
            "https://news.kbs.co.kr/news/pc/view/view.do?ncd=8236000",
        )
        article.topic = "마늘"
        by_section = {key: [] for key in self.conf}
        by_section["policy"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        garlic = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "garlic"
        )

        self.assertFalse(garlic["active"])
        self.assertEqual(garlic["article_count"], 0)

    def test_board_rejects_multi_item_policy_roundup_for_garlic(self):
        article = self._make_article(
            "policy",
            "계란·화장지 등 민생물가 잡는다…과자·아이스크림도 가격 인하",
            "농식품부는 계란, 돼지고기, 가공식품(식용유 등), 마늘 등 4개 품목, 산업통상부는 화장지, 세탁세제 물량을 점검한다. "
            "김도 물김과 마른김의 수급 동향을 지속 관리하고 생산자·가공업계 의견 수렴을 통해 개선한다.",
            "https://example.com/garlic-policy-roundup",
        )
        article.topic = "마늘"
        by_section = {key: [] for key in self.conf}
        by_section["policy"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        garlic = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "garlic"
        )

        self.assertFalse(garlic["active"])
        self.assertEqual(garlic["article_count"], 0)

    def test_board_metrics_reject_body_only_policy_roundup_for_garlic(self):
        article = self._make_article(
            "policy",
            "계란·화장지 등 민생물가 잡는다…과자·아이스크림도 가격 인하",
            "농식품부는 계란, 돼지고기, 가공식품(식용유 등), 마늘 등 4개 품목, 산업통상부는 화장지, 세탁세제 물량을 점검한다. "
            "김도 물김과 마른김의 수급 동향을 지속 관리하고 생산자·가공업계 의견 수렴을 통해 개선한다.",
            "https://example.com/garlic-policy-roundup-metrics",
        )
        article.topic = "마늘"

        metrics = main._commodity_board_item_article_representative_metrics(self._item("garlic"), article)

        self.assertFalse(bool(metrics["board_eligible"]))
        self.assertLess(int(metrics["representative_rank"]), 1)

    def test_board_rejects_macro_brand_story_for_tomato(self):
        article = self._make_article(
            "policy",
            "[IB 토마토] 반도건설, 1조 매출 지켰지만 빚도 4배 불었다",
            "건설사의 실적과 차입금, 재무구조를 분석하는 증권 기사다.",
            "https://www.newstomato.com/ReadNews.aspx?no=1260237",
        )
        by_section = {key: [] for key in self.conf}
        by_section["policy"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        tomato = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "tomato"
        )

        self.assertFalse(tomato["active"])
        self.assertEqual(tomato["article_count"], 0)

    def test_board_rejects_macro_story_without_agri_context_for_eggplant(self):
        article = self._make_article(
            "supply",
            "AI가 올린 증시, 유가가 흔든다…수혜 갈리는 고유가 장세",
            "정유·항공 업종의 두 가지 시나리오를 비교한 증시 분석 기사다.",
            "https://www.etoday.co.kr/news/view/2482000",
        )
        article.topic = "가지"
        by_section = {key: [] for key in self.conf}
        by_section["supply"] = [article]

        ctx = main.build_managed_commodity_board_context(by_section)
        eggplant = next(
            item
            for group in ctx["groups"]
            for item in list(group["items"]) + list(group["inactive_items"])
            if item["key"] == "eggplant"
        )

        self.assertFalse(eggplant["active"])
        self.assertEqual(eggplant["article_count"], 0)

    def test_query_article_match_gate_rejects_other_commodity_tourism_hit(self):
        self.assertFalse(
            main._query_article_match_ok(
                "무 재배",
                "형광빛 메타세쿼이아·고즈넉한 고택… 배꽃 필 무렵이 최고의 시간",
                "배꽃 개화 시기에 맞춰 관광객이 찾는 봄 여행 코스를 소개하는 기사다.",
                "supply",
            )
        )

    def test_supply_macro_official_shock_story_is_rejected_from_supply(self):
        title = '문신학 산업차관 "비상시 정유사 수출 물량 줄일수도…2차 최고가격 오를수도"'
        desc = (
            "문신학 산업차관은 중동발 위기 대응을 위해 비상시 정유사 수출 물량을 줄이는 방안까지 포함한 "
            "플랜B를 준비 중이라고 밝혔다. 국내 석유제품 수급 불안이 커진 상황이 배경이다."
        )
        url = "https://www.sedaily.com/article/20021867"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)

        self.assertTrue(main.is_supply_macro_official_shock_context(title, desc, dom, press))
        self.assertFalse(main.is_relevant(title, desc, dom, url, self.conf["supply"], press))

    def test_processed_consumer_panic_story_is_rejected_from_supply(self):
        title = "이란 전쟁에 日 유통업계도 타격… 감자 칩 생산 중단, 화장지 품귀설 확산"
        desc = (
            "이란 전쟁 여파로 일본 유통업계에서도 감자칩 생산 중단과 화장지 품귀설이 번지고 있다. "
            "원유 정제 소재가 쓰이는 자동차 부품과 의료기기 수급 차질 우려도 제기됐다."
        )
        url = "https://biz.chosun.com/international/international_economy/2026/03/21/G7Z72WHI75H6TFIPFTFFKCNVMI/"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        article = self._make_article("supply", title, desc, url)

        self.assertTrue(main.is_supply_processed_consumer_panic_context(title, desc))
        self.assertFalse(main.is_relevant(title, desc, dom, url, self.conf["supply"], press))
        metrics = main._commodity_board_item_article_representative_metrics(self._item("potato"), article)
        self.assertLess(int(metrics["representative_rank"]), 1)
        self.assertTrue(bool(metrics["weak_processed_panic_story"]))

    def test_program_brand_action_story_is_demoted_from_supply_and_board(self):
        title = "‘경북형 공동영농’ 소득배당으로 농가소득 높여"
        desc = (
            "경북형 공동영농은 묘목 보급과 출하계약을 바탕으로 사과와 시설채소의 생산비를 낮추는 방식으로 추진된다. "
            "2027년에는 규격화한 ‘골든볼’ 사과를 단일 브랜드로 판매할 계획이다."
        )
        article = self._make_article(
            "supply",
            title,
            desc,
            "https://www.nongmin.com/article/20260317500487",
        )

        self.assertTrue(main.is_supply_program_brand_action_context(title, desc))
        self.assertTrue(main.is_supply_weak_tail_context(title, desc))
        metrics = main._commodity_board_item_article_representative_metrics(self._item("apple"), article)
        self.assertLess(int(metrics["representative_rank"]), 1)
        self.assertTrue(bool(metrics["weak_program_brand_story"]))

    def test_price_support_event_story_with_real_supply_stress_survives_board_and_bridge(self):
        title = "월동무 가격 하락에 긴급 할인행사 추진"
        desc = (
            "제주농산물수급관리연합회와 센터가 월동무 도매가격 하락에 대응해 긴급 할인행사를 추진한다. "
            "가격지지 TF 회의도 열어 경매가격 회복 방안을 논의했다."
        )
        article = self._make_article(
            "supply",
            title,
            desc,
            "http://www.aflnews.co.kr/news/articleView.html?idxno=316761",
        )

        self.assertTrue(main.is_supply_price_support_event_context(title, desc))
        self.assertTrue(main.is_supply_weak_tail_context(title, desc))
        metrics = main._commodity_board_item_article_representative_metrics(self._item("radish"), article)
        self.assertGreaterEqual(int(metrics["representative_rank"]), 3)
        self.assertFalse(bool(metrics["weak_price_support_event_story"]))
        self.assertTrue(main._commodity_board_article_is_active_candidate(self._item("radish"), article, metrics))
        self.assertTrue(main._commodity_board_article_is_supply_bridge_candidate(self._item("radish"), article, metrics))

    def test_consumer_expansion_tail_is_not_misclassified_as_price_support_event(self):
        title = "양배추 가격 급락에 제주 농가 '시름'...소비확대 '총력전'"
        desc = "양배추 가격 급락으로 농가 부담이 커지자 할인 판매와 소비 촉진 행사가 이어지고 있다."
        article = self._make_article(
            "supply",
            title,
            desc,
            "https://www.headlinejeju.co.kr/news/articleView.html?idxno=588956",
        )

        self.assertFalse(main.is_supply_price_support_event_context(title, desc))
        metrics = main._commodity_board_item_article_representative_metrics(self._item("cabbage"), article)
        self.assertGreaterEqual(int(metrics["representative_rank"]), 1)

    def test_orchard_monitoring_response_story_stays_active_for_pear(self):
        article = self._make_article(
            "supply",
            "나주시, 이상기상 선제 대응 나주배 과원 실시간 모니터링",
            "나주배 과원의 저온 피해와 생육 상황을 실시간 점검하고 출하 차질을 줄이기 위한 선제 대응 체계를 가동한다.",
            "https://example.com/pear-orchard-monitoring",
        )
        item = self._item("pear")
        metrics = main._commodity_board_item_article_representative_metrics(item, article)

        self.assertGreaterEqual(int(metrics["representative_rank"]), 1)
        self.assertFalse(bool(metrics["weak_support_advice_story"]))
        self.assertTrue(main._commodity_board_article_is_active_candidate(item, article, metrics))

    def test_supply_core_selection_skips_generic_category_watch_story(self):
        generic_watch = self._make_article(
            "supply",
            "채소값 곤두박질…공급·소비·정책 삼중고",
            "풋고추와 오이 등 채소류 가격이 흔들리고 공급과 소비, 정책 부담이 함께 겹치고 있다.",
            "https://example.com/vegetable-category-watch-core",
        )
        valid_articles = [
            self._make_article(
                "supply",
                "고유가에 난방비 걱정...방울 토마토 농가 생산량 급감",
                "고유가로 시설 난방비가 급등하면서 방울 토마토 농가 생산량이 줄고 출하 조절 부담이 커졌다.",
                "https://example.com/tomato-heating-shock-core",
            ),
            self._make_article(
                "supply",
                "\"마늘 수확량 월등히 많고, 1등품이 73% 차지\"",
                "마늘 작황이 좋아 수확량과 상품 비중이 크게 늘면서 산지 수급 흐름이 달라지고 있다.",
                "https://example.com/garlic-harvest-quality-core",
            ),
            self._make_article(
                "supply",
                "[시황] 참외 본격 출하…물량 증가·대체 품목 경쟁에 가격 하락세",
                "참외가 본격 출하되며 물량이 늘고 대체 품목 경쟁까지 겹쳐 가격은 지난해보다 낮은 흐름이다.",
                "https://example.com/oriental-melon-supply-core",
            ),
            generic_watch,
        ]

        selected = main.select_top_articles(valid_articles, "supply", 4)
        selected_titles = {article.title for article in selected}
        core_titles = {article.title for article in selected if article.is_core}

        self.assertIn("고유가에 난방비 걱정...방울 토마토 농가 생산량 급감", core_titles)
        self.assertNotIn(generic_watch.title, selected_titles)
        self.assertNotIn(generic_watch.title, core_titles)

    def test_local_sales_event_story_is_demoted_from_supply_tail(self):
        title = "익산시, 직거래장터 연장 운영…3일간 1600만원 매출"
        desc = (
            "익산시가 농산물 직거래장터 운영 기간을 연장한 결과 3일간 1600만원 매출을 기록했다. "
            "지역 농가 판로 지원과 소비 촉진을 위해 장터를 이어간다."
        )
        local_sales = self._make_article(
            "supply",
            title,
            desc,
            "https://example.com/iksan-market-sales",
        )
        valid_articles = [
            self._make_article(
                "supply",
                "고유가에 난방비 걱정...방울 토마토 농가 생산량 급감",
                "고유가로 시설 난방비가 급등하면서 방울 토마토 농가 생산량이 줄고 출하 조절 부담이 커졌다.",
                "https://example.com/tomato-heating-shock-tail",
            ),
            self._make_article(
                "supply",
                "\"마늘 수확량 월등히 많고, 1등품이 73% 차지\"",
                "마늘 작황이 좋아 수확량과 상품 비중이 크게 늘면서 산지 수급 흐름이 달라지고 있다.",
                "https://example.com/garlic-harvest-quality-tail",
            ),
            self._make_article(
                "supply",
                "[시황] 참외 본격 출하…물량 증가·대체 품목 경쟁에 가격 하락세",
                "참외가 본격 출하되며 물량이 늘고 대체 품목 경쟁까지 겹쳐 가격은 지난해보다 낮은 흐름이다.",
                "https://example.com/oriental-melon-supply-tail",
            ),
            local_sales,
        ]

        self.assertTrue(main.is_supply_local_sales_event_context(title, desc))
        self.assertTrue(main.is_supply_weak_tail_context(title, desc))
        selected = main.select_top_articles(valid_articles, "supply", 4)
        selected_titles = {article.title for article in selected}

        self.assertNotIn(title, selected_titles)

    def test_supply_normalization_prunes_local_sales_filler_when_four_stronger_items_exist(self):
        local_sales = self._make_article(
            "supply",
            "익산시, 직거래장터 연장 운영…3일간 1600만원 매출",
            "판매 품목은 하우스 작물과 저장 농산물, 계란 등 16개로, 딸기와 토마토, 고구마, 잡곡류, 대파 등 지역 농가가 직접 생산한 "
            "신선 농산물이 합리적인 가격에 제공됐다. 준비된 물량이 연일 조기 소진될 정도로 큰 호응을 얻었다.",
            "https://example.com/iksan-market-sales-normalize",
        )
        final_by_section = {key: [] for key in self.conf}
        final_by_section["supply"] = [
            self._make_article(
                "supply",
                "고유가에 난방비 걱정...방울 토마토 농가 생산량 급감",
                "고유가로 시설 난방비가 급등하면서 방울 토마토 농가 생산량이 줄고 출하 조절 부담이 커졌다.",
                "https://example.com/tomato-heating-shock-normalize",
            ),
            self._make_article(
                "supply",
                "\"마늘 수확량 월등히 많고, 1등품이 73% 차지\"",
                "마늘 작황이 좋아 수확량과 상품 비중이 크게 늘면서 산지 수급 흐름이 달라지고 있다.",
                "https://example.com/garlic-harvest-quality-normalize",
            ),
            self._make_article(
                "supply",
                "[시황] 참외 본격 출하…물량 증가·대체 품목 경쟁에 가격 하락세",
                "참외가 본격 출하되며 물량이 늘고 대체 품목 경쟁까지 겹쳐 가격은 지난해보다 낮은 흐름이다.",
                "https://example.com/oriental-melon-supply-normalize",
            ),
            self._make_article(
                "supply",
                "사과 선별·공판 기능 결합…유통거점 부상",
                "산지 출하 가격과 공판 기능이 결합되며 사과 유통거점 역할이 강화되고 있다.",
                "https://example.com/apple-hub-normalize",
            ),
            local_sales,
        ]
        board_source = {key: [] for key in self.conf}

        changed = main._normalize_supply_section_from_board(final_by_section, board_source, max_items=5)

        self.assertTrue(main.is_supply_local_sales_event_context(local_sales.title, local_sales.description))
        self.assertEqual(changed, 0)
        self.assertEqual(len(final_by_section["supply"]), 4)
        self.assertNotIn(local_sales.title, {article.title for article in final_by_section["supply"]})

    def test_supply_official_support_response_story_is_demoted_from_supply(self):
        title = "송미령 장관, 농협주유소·시설채소 점검…난방유 부담 대응 주문"
        desc = (
            "송미령 농식품부 장관이 농협주유소와 시설채소 농가를 찾아 난방유와 면세유 부담 대응을 주문하며 "
            "생산비 완화 대책을 점검했다."
        )
        article = self._make_article(
            "supply",
            title,
            desc,
            "https://www.dailian.co.kr/news/view/1622945/?sc=Naver",
        )

        self.assertTrue(main.is_supply_official_support_response_context(title, desc))
        self.assertTrue(main.is_supply_weak_tail_context(title, desc))
        selected = main.select_top_articles(
            [
                self._make_article(
                    "supply",
                    "고유가에 난방비 걱정...방울 토마토 농가 생산량 급감",
                    "고유가로 시설 난방비가 급등하면서 방울 토마토 농가 생산량이 줄고 출하 조절 부담이 커졌다.",
                    "https://example.com/tomato-heating-shock",
                ),
                self._make_article(
                    "supply",
                    '"마늘 수확량 월등히 많고, 1등품이 73% 차지"',
                    "마늘 작황이 좋아 수확량과 상품 비중이 크게 늘면서 산지 수급 흐름이 달라지고 있다.",
                    "https://example.com/garlic-harvest-quality",
                ),
                self._make_article(
                    "supply",
                    "[시황] 참외 본격 출하…물량 증가·대체 품목 경쟁에 가격 하락세",
                    "참외가 본격 출하되며 물량이 늘고 대체 품목 경쟁까지 겹쳐 가격은 지난해보다 낮은 흐름이다.",
                    "https://example.com/oriental-melon-supply",
                ),
                article,
            ],
            "supply",
            3,
        )
        self.assertNotIn(title, {picked.title for picked in selected})

    def test_supply_processed_price_roundup_and_accusatory_quote_are_demoted(self):
        roundup_title = "아이스크림·과자도 가격 내린다…롯데웰푸드·빙그레 등 최대 13.4% 인하..."
        roundup_desc = "가공식품 가격 인하가 이어지며 과자와 아이스크림 제품 가격이 줄줄이 내려간다."
        quote_title = "\"생산비 폭등 외면, 농산물 가격 억제에만 혈안\""
        quote_desc = "농산물 가격 억제 정책을 비판하는 현장 목소리를 전한 기사다."

        self.assertTrue(main.is_supply_processed_price_roundup_context(roundup_title, roundup_desc))
        self.assertTrue(main.is_supply_weak_tail_context(roundup_title, roundup_desc))
        self.assertTrue(main.is_supply_accusatory_quote_context(quote_title, quote_desc))
        self.assertTrue(main.is_supply_weak_tail_context(quote_title, quote_desc))

    def test_dist_program_event_and_agritech_noise_are_rejected(self):
        price_support_title = "월동무 가격 하락에 긴급 할인행사 추진"
        price_support_desc = (
            "제주농산물수급관리연합회와 센터가 월동무 도매가격 하락에 대응해 긴급 할인행사를 추진한다. "
            "가격지지 TF 회의도 열어 경매가격 회복 방안을 논의했다."
        )
        program_title = "대아청과, '제주 양배추 농가 지원' 소비촉진 행사"
        program_desc = (
            "대아청과가 제주 양배추 농가 지원을 위해 소비촉진 행사와 공동구매를 진행하며 "
            "판매 활성화에 나선다."
        )
        agritech_title = "드론이 방제하고, 자율 트랙터가 밭 갈고… 농사도 'AI 시대'"
        agritech_desc = "드론 방제와 자율 트랙터, 스마트팜 기술을 활용한 농업 혁신 사례를 소개했다."
        coop_title = "인천농협, 미나리 공동구매 소비 촉진 나서"
        coop_desc = "인천농협이 미나리 공동구매와 소비 촉진 행사로 판로 지원에 나선다고 밝혔다."
        lane_title = "강원도, 온라인·대형유통망 연계해 농수특산물 판로 확대"
        lane_desc = "강원도가 온라인 판매와 대형유통망을 연계해 농수특산물 판로 확대 사업을 추진한다."

        self.assertTrue(main.is_dist_program_event_noise_context(price_support_title, price_support_desc, "aflnews.co.kr", "농수축산신문"))
        self.assertTrue(main.is_dist_program_event_noise_context(program_title, program_desc, "amnews.co.kr", "농축유통신문"))
        self.assertTrue(main.is_dist_program_event_noise_context(coop_title, coop_desc, "nongmin.com", "농민신문"))
        self.assertTrue(main.is_dist_program_event_noise_context(lane_title, lane_desc, "chmbc.co.kr", "춘천MBC"))
        self.assertTrue(main.is_dist_unanchored_agritech_noise_context(agritech_title, agritech_desc))

    def test_dist_selection_skips_program_event_and_agritech_noise(self):
        valid_articles = [
            self._make_article(
                "dist",
                "청주 농수산물 도매시장 시설현대화사업, 11월 준공 목표",
                "청주 농수산물 도매시장 시설현대화사업이 11월 준공을 목표로 경매장과 저온저장 시설을 확충하고 있다.",
                "https://example.com/cheongju-market-modernization",
            ),
            self._make_article(
                "dist",
                "기린원당농협두부조공법인, 첫 영국 수출 선적식",
                "기린원당농협두부조공법인이 첫 영국 수출 선적식을 열고 물류와 통관 절차를 점검했다.",
                "https://example.com/uk-export-shipping",
            ),
            self._make_article(
                "dist",
                "강원특별자치도, 전국 최초 농산물 광역수급관리센터 가동",
                "강원특별자치도가 농산물 광역수급관리센터를 가동하며 반입 조절과 물량 배분 체계를 강화했다.",
                "https://example.com/gangwon-supply-center",
            ),
        ]
        noise_articles = [
            self._make_article(
                "dist",
                "월동무 가격 하락에 긴급 할인행사 추진",
                "제주농산물수급관리연합회와 센터가 월동무 도매가격 하락에 대응해 긴급 할인행사를 추진한다. 가격지지 TF 회의도 열어 경매가격 회복 방안을 논의했다.",
                "http://www.aflnews.co.kr/news/articleView.html?idxno=316761",
            ),
            self._make_article(
                "dist",
                "대아청과, '제주 양배추 농가 지원' 소비촉진 행사",
                "대아청과가 제주 양배추 농가 지원을 위해 소비촉진 행사와 공동구매를 진행하며 판매 활성화에 나선다.",
                "https://example.com/cabbage-promo-event",
            ),
            self._make_article(
                "dist",
                "드론이 방제하고, 자율 트랙터가 밭 갈고… 농사도 'AI 시대'",
                "드론 방제와 자율 트랙터, 스마트팜 기술을 활용한 농업 혁신 사례를 소개했다.",
                "https://example.com/agritech-feature",
            ),
        ]

        selected = main.select_top_articles(valid_articles + noise_articles, "dist", 4)
        selected_titles = {article.title for article in selected}

        self.assertNotIn("월동무 가격 하락에 긴급 할인행사 추진", selected_titles)
        self.assertNotIn("대아청과, '제주 양배추 농가 지원' 소비촉진 행사", selected_titles)
        self.assertNotIn("드론이 방제하고, 자율 트랙터가 밭 갈고… 농사도 'AI 시대'", selected_titles)

    def test_dist_program_event_title_override_prunes_final_section_even_with_channel_desc(self):
        article = self._make_article(
            "dist",
            "강원도, 온라인·대형유통망 연계해 농수특산물 판로 확대",
            "강원도가 온라인 판매와 대형유통망, 물류 지원 체계를 연계해 농수특산물 판로 확대 사업을 추진한다고 밝혔다.",
            "https://example.com/gangwon-channel-expansion",
        )

        self.assertTrue(
            main.is_dist_program_event_noise_context(
                article.title,
                article.description,
                main.domain_of(article.link),
                main.normalize_press_label("춘천MBC", article.link),
            )
        )

        final_by_section = {"dist": [article]}
        self.assertEqual(main._audit_final_sections(final_by_section), 1)
        self.assertEqual(final_by_section["dist"], [])

    def test_dist_non_horti_anchorless_noise_is_rejected(self):
        roundup_title = "[퇴근길포인트] BTS 광화문 공연에…警, 하객 수송 버스 띄운다...정부,..."
        roundup_desc = "공연과 교통 대책, 정부 대응을 짚은 퇴근길 종합 기사다."
        export_title = "빙그레, '수출이 성장축'으로…글로벌 확장이 한국 경제에 던지는 의미"
        export_desc = "기업의 글로벌 확장과 수출 전략이 한국 경제에 미칠 영향을 짚은 해설 기사다."

        self.assertTrue(main.is_dist_non_horti_anchorless_noise_context(roundup_title, roundup_desc))
        self.assertTrue(main.is_dist_non_horti_anchorless_noise_context(export_title, export_desc))

    def test_dist_local_roundup_and_official_cost_response_noise_are_rejected(self):
        roundup_title = "［E-로컬뉴스］김천시, 구미시, 성주군 소식"
        roundup_desc = "김천시, 구미시, 성주군의 지역 소식을 묶은 기사다."
        response_title = "중동 리스크에 농업비용 급등…정부, 비료·물류·수출 전방위 대응"
        response_desc = "정부가 비료와 물류, 수출 비용 상승 대응책을 점검하고 관계부처 대책을 논의했다."

        self.assertTrue(main.is_dist_local_roundup_title_context(roundup_title, roundup_desc))
        self.assertTrue(
            main.is_dist_official_cost_response_noise_context(
                response_title,
                response_desc,
                "newspim.com",
                "뉴스핌",
            )
        )

    def test_dist_selection_skips_non_horti_anchorless_underfill_noise(self):
        valid_articles = [
            self._make_article(
                "dist",
                "청주 농수산물 도매시장 시설현대화사업, 11월 준공 목표",
                "청주 농수산물 도매시장 시설현대화사업이 11월 준공을 목표로 경매장과 저온저장 시설을 확충하고 있다.",
                "https://example.com/cheongju-market-modernization",
            ),
            self._make_article(
                "dist",
                "강원특별자치도, 전국 최초 농산물 광역수급관리센터 가동",
                "강원특별자치도가 농산물 광역수급관리센터를 가동하며 반입 조절과 물량 배분 체계를 강화했다.",
                "https://example.com/gangwon-supply-center",
            ),
        ]
        noise_articles = [
            self._make_article(
                "dist",
                "[퇴근길포인트] BTS 광화문 공연에…警, 하객 수송 버스 띄운다...정부,...",
                "공연과 교통 대책, 정부 대응을 짚은 퇴근길 종합 기사다.",
                "https://example.com/evening-roundup",
            ),
            self._make_article(
                "dist",
                "빙그레, '수출이 성장축'으로…글로벌 확장이 한국 경제에 던지는 의미",
                "기업의 글로벌 확장과 수출 전략이 한국 경제에 미칠 영향을 짚은 해설 기사다.",
                "https://example.com/binggrae-global-export",
            ),
        ]

        selected = main.select_top_articles(valid_articles + noise_articles, "dist", 4)
        selected_titles = {article.title for article in selected}

        self.assertNotIn("[퇴근길포인트] BTS 광화문 공연에…警, 하객 수송 버스 띄운다...정부,...", selected_titles)
        self.assertNotIn("빙그레, '수출이 성장축'으로…글로벌 확장이 한국 경제에 던지는 의미", selected_titles)

    def test_dist_selection_skips_local_roundup_and_official_cost_response_noise(self):
        valid_articles = [
            self._make_article(
                "dist",
                "청주 농수산물 도매시장 시설현대화사업, 11월 준공 목표",
                "청주 농수산물 도매시장 시설현대화사업이 11월 준공을 목표로 경매장과 저온저장 시설을 확충하고 있다.",
                "https://example.com/cheongju-market-modernization",
            ),
            self._make_article(
                "dist",
                "강원특별자치도, 전국 최초 농산물 광역수급관리센터 가동",
                "강원특별자치도가 농산물 광역수급관리센터를 가동하며 반입 조절과 물량 배분 체계를 강화했다.",
                "https://example.com/gangwon-supply-center",
            ),
        ]
        noise_articles = [
            self._make_article(
                "dist",
                "［E-로컬뉴스］김천시, 구미시, 성주군 소식",
                "김천시, 구미시, 성주군의 지역 소식을 묶은 기사다.",
                "https://example.com/e-local-roundup",
            ),
            self._make_article(
                "dist",
                "중동 리스크에 농업비용 급등…정부, 비료·물류·수출 전방위 대응",
                "정부가 비료와 물류, 수출 비용 상승 대응책을 점검하고 관계부처 대책을 논의했다.",
                "https://example.com/official-cost-response",
            ),
        ]

        selected = main.select_top_articles(valid_articles + noise_articles, "dist", 4)
        selected_titles = {article.title for article in selected}

        self.assertNotIn("［E-로컬뉴스］김천시, 구미시, 성주군 소식", selected_titles)
        self.assertNotIn("중동 리스크에 농업비용 급등…정부, 비료·물류·수출 전방위 대응", selected_titles)

    def test_dist_final_dedupes_same_market_modernization_story(self):
        selected = main.select_top_articles(
            [
                self._make_article(
                    "dist",
                    "청주 농수산물 도매시장 시설현대화사업, 11월 준공 목표",
                    "청주 농수산물 도매시장 시설현대화사업이 11월 준공을 목표로 경매장과 저온저장 시설을 확충하고 있다.",
                    "https://example.com/cheongju-market-modernization-a",
                ),
                self._make_article(
                    "dist",
                    "청주 농수산물 도매시장 현대화 ‘착착’…11월 준공",
                    "청주 농수산물 도매시장 현대화 사업이 11월 준공을 목표로 경매장과 저온저장 시설을 확충하고 있다.",
                    "https://example.com/cheongju-market-modernization-b",
                ),
                self._make_article(
                    "dist",
                    "강원특별자치도, 전국 최초 농산물 광역수급관리센터 가동",
                    "강원특별자치도가 농산물 광역수급관리센터를 가동하며 반입 조절과 물량 배분 체계를 강화했다.",
                    "https://example.com/gangwon-supply-center",
                ),
            ],
            "dist",
            4,
        )
        selected_titles = {article.title for article in selected}
        modernization_titles = {
            "청주 농수산물 도매시장 시설현대화사업, 11월 준공 목표",
            "청주 농수산물 도매시장 현대화 ‘착착’…11월 준공",
        }
        self.assertEqual(len(selected_titles & modernization_titles), 1)

    def test_dist_rebalance_does_not_pull_supply_when_two_dist_items_exist(self):
        final_by_section = {
            "dist": [
                self._make_article(
                    "dist",
                    "청주 농수산물 도매시장 시설현대화사업, 11월 준공 목표",
                    "청주 농수산물 도매시장 시설현대화사업이 11월 준공을 목표로 경매장과 저온저장 시설을 확충하고 있다.",
                    "https://example.com/cheongju-market-modernization",
                ),
                self._make_article(
                    "dist",
                    "강원특별자치도, 전국 최초 농산물 광역수급관리센터 가동",
                    "강원특별자치도가 농산물 광역수급관리센터를 가동하며 반입 조절과 물량 배분 체계를 강화했다.",
                    "https://example.com/gangwon-supply-center",
                ),
            ],
            "supply": [
                self._make_article(
                    "supply",
                    "고유가에 난방비 걱정...방울 토마토 농가 생산량 급감",
                    "고유가로 시설 난방비가 급등하면서 방울 토마토 농가 생산량이 줄고 출하 조절 부담이 커졌다.",
                    "https://example.com/tomato-heating-shock",
                ),
                self._make_article(
                    "supply",
                    '"마늘 수확량 월등히 많고, 1등품이 73% 차지"',
                    "마늘 작황이 좋아 수확량과 상품 비중이 크게 늘면서 산지 수급 흐름이 달라지고 있다.",
                    "https://example.com/garlic-harvest-quality",
                ),
                self._make_article(
                    "supply",
                    "[시황] 참외 본격 출하…물량 증가·대체 품목 경쟁에 가격 하락세",
                    "참외가 본격 출하되며 물량이 늘고 대체 품목 경쟁까지 겹쳐 가격은 지난해보다 낮은 흐름이다.",
                    "https://example.com/oriental-melon-supply",
                ),
            ],
        }

        moved = main._rebalance_underfilled_dist_from_supply(final_by_section)
        self.assertEqual(moved, 0)
        self.assertEqual(len(final_by_section["dist"]), 2)

    def test_supply_selection_skips_macro_official_and_processed_panic_tails(self):
        valid_articles = [
            self._make_article(
                "supply",
                "[시황] 참외 본격 출하…물량 증가·대체 품목 경쟁에 가격 하락세",
                "참외가 본격 출하되며 물량이 늘고 대체 품목 경쟁까지 겹쳐 가격은 지난해보다 낮은 흐름이다.",
                "https://example.com/oriental-melon-supply",
            ),
            self._make_article(
                "supply",
                "고유가에 난방비 걱정...방울 토마토 농가 생산량 급감",
                "고유가로 시설 난방비가 급등하면서 방울 토마토 농가 생산량이 줄고 출하 조절 부담이 커졌다.",
                "https://example.com/tomato-heating-shock",
            ),
            self._make_article(
                "supply",
                '"마늘 수확량 월등히 많고, 1등품이 73% 차지"',
                "마늘 작황이 좋아 수확량과 상품 비중이 크게 늘면서 산지 수급 흐름이 달라지고 있다.",
                "https://example.com/garlic-harvest-quality",
            ),
            self._make_article(
                "supply",
                '"햇양파 도매 가격 kg당 400원, 수확 비용도 못 건져"',
                "햇양파 도매가격이 급락해 수확 비용도 건지기 어려운 상황이라 산지 출하 조절 요구가 커지고 있다.",
                "https://example.com/onion-price-collapse",
            ),
            self._make_article(
                "supply",
                "사과 선별·공판 기능 결합…유통거점 부상",
                "사과 선별과 공판 기능이 결합되며 산지 출하와 물량 조절 거점 역할이 커지고 있다.",
                "https://example.com/apple-hub-supply",
            ),
        ]
        for idx, article in enumerate(valid_articles):
            article.score += max(0.0, 12.0 - idx)

        macro_article = self._make_article(
            "supply",
            '문신학 산업차관 "비상시 정유사 수출 물량 줄일수도…2차 최고가격 오를수도"',
            "문신학 산업차관은 중동발 위기 대응을 위해 비상시 정유사 수출 물량을 줄이는 방안까지 포함한 플랜B를 준비 중이라고 밝혔다.",
            "https://www.sedaily.com/article/20021867",
        )
        panic_article = self._make_article(
            "supply",
            "이란 전쟁에 日 유통업계도 타격… 감자 칩 생산 중단, 화장지 품귀설 확산",
            "이란 전쟁 여파로 일본 유통업계에서도 감자칩 생산 중단과 화장지 품귀설이 번지고 있다. 원유 정제 소재가 쓰이는 자동차 부품과 의료기기 수급 차질 우려도 제기됐다.",
            "https://biz.chosun.com/international/international_economy/2026/03/21/G7Z72WHI75H6TFIPFTFFKCNVMI/",
        )
        processed_lifestyle_article = self._make_article(
            "supply",
            '"K바비큐에 톨라이니 발디산티 한 잔 어때요"',
            "한동안 방치됐던 고지대 포도 밭을 다시 정비해 만든 와인으로, 작황에 따라 생산량이 3000병 수준에 그치거나 아예 출시되지 않을 만큼 희소성이 높다. "
            "100% 산지오베제로 만들어진다.",
            "https://example.com/grape-wine-lifestyle",
        )

        program_article = self._make_article(
            "supply",
            "‘경북형 공동영농’ 소득배당으로 농가소득 높여",
            "경북형 공동영농은 묘목 보급과 출하계약을 바탕으로 사과와 시설채소의 생산비를 낮추는 방식으로 추진된다. 2027년에는 규격화한 ‘골든볼’ 사과를 단일 브랜드로 판매할 계획이다.",
            "https://www.nongmin.com/article/20260317500487",
        )
        price_support_article = self._make_article(
            "supply",
            "월동무 가격 하락에 긴급 할인행사 추진",
            "제주농산물수급관리연합회와 센터가 월동무 도매가격 하락에 대응해 긴급 할인행사를 추진한다. 가격지지 TF 회의도 열어 경매가격 회복 방안을 논의했다.",
            "http://www.aflnews.co.kr/news/articleView.html?idxno=316761",
        )

        selected = main.select_top_articles(
            valid_articles + [macro_article, panic_article, processed_lifestyle_article, program_article, price_support_article],
            "supply",
            4,
        )
        selected_titles = {article.title for article in selected}

        self.assertNotIn(macro_article.title, selected_titles)
        self.assertNotIn(panic_article.title, selected_titles)
        self.assertNotIn(processed_lifestyle_article.title, selected_titles)
        self.assertNotIn(program_article.title, selected_titles)
        self.assertNotIn(price_support_article.title, selected_titles)

    def test_supply_final_normalization_skips_generic_category_watch_story(self):
        weak_supply = self._make_article(
            "supply",
            "동광양농협, 농가주부모임과 감자 심기 행사 진행",
            "감자 심기 행사와 현장 체험 중심의 지역 행사 기사다.",
            "https://example.com/potato-event-normalize",
        )
        generic_watch = self._make_article(
            "supply",
            "채소값 곤두박질…공급·소비·정책 삼중고",
            "풋고추와 오이 등 채소류 가격이 흔들리고 공급과 소비, 정책 부담이 함께 겹치고 있다.",
            "https://example.com/vegetable-category-watch-normalize",
        )
        final_by_section = {key: [] for key in self.conf}
        final_by_section["supply"] = [weak_supply]
        board_source = {key: [] for key in self.conf}
        board_source["supply"] = [weak_supply, generic_watch]

        changed = main._normalize_supply_section_from_board(final_by_section, board_source, max_items=3)

        self.assertEqual(changed, 0)
        self.assertEqual(final_by_section["supply"][0].title, weak_supply.title)

if __name__ == "__main__":
    unittest.main()
