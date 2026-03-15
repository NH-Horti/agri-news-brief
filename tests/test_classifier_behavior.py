import unittest
from datetime import datetime, timedelta
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


class TestClassifierBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conf = {s["key"]: s for s in main.SECTIONS}
        cls.now = datetime.now(main.KST)

    def setUp(self):
        main.reset_extra_call_budget()

    def _best_section(self, title: str, desc: str, url: str):
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        scores = {}
        for key, conf in self.conf.items():
            if main.is_relevant(title, desc, dom, url, conf, press):
                scores[key] = main.compute_rank_score(title, desc, dom, self.now, conf, press)
        return (max(scores, key=scores.get) if scores else None), scores
    def _make_article(self, section: str, title: str, desc: str, url: str):
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

    def test_market_relocation_prefers_dist(self):
        title = "광주 각화농산물 시장, 효령동 일원으로 옮긴다"
        desc = "광주 각화농산물 시장이 효령동으로 이전하며 물량 조절 기능을 강화해 농산물 수급과 가격 안정성을 확보한다."
        best, scores = self._best_section(title, desc, "https://m.seoul.co.kr/news/society/2026/03/02/20260302500115?wlog_tag3=naver")
        self.assertEqual(best, "dist", msg=f"scores={scores}")

    def test_newdaily_mapping(self):
        p = main.normalize_press_label("newdaily", "https://biz.newdaily.co.kr/site/data/html/2026/02/27/2026022700154.html")
        self.assertEqual(p, "뉴데일리경제")

    def test_rice_pest_article_is_excluded_for_horti_scope(self):
        t1 = "고성군, 벼 병해충 방제 업무 연찬회 가져"
        d1 = "고성군은 벼 병해충 방제를 위한 업무 연찬회를 개최하고 행정적 지원과 예찰 강화를 추진한다."
        best1, scores1 = self._best_section(t1, d1, "https://www.newsgn.com/news/articleView.html?idxno=537277")
        self.assertIsNone(best1, msg=f"scores={scores1}")

    def test_orchard_fire_blight_article_prefers_pest(self):
        t2 = "진주시, 과수화상병 예방 교육·약제… 3회분 무상공급"
        d2 = "진주시는 과수화상병 방제를 위해 382개 농가에 총 3회분의 약제를 무상으로 공급한다고 밝혔다."
        best2, scores2 = self._best_section(t2, d2, "https://mobile.newsis.com/view/NISX20260228_0003530198")
        self.assertEqual(best2, "pest", msg=f"scores={scores2}")

    def test_youngnong_tomato_moth_control_article_prefers_pest(self):
        title = "경기도, 토마토 재배 농가 전수조사… 토마토뿔나방 방제 지원"
        desc = "경기도는 토마토뿔나방 확산 대응을 위해 재배 농가 전수조사를 실시하고 예찰·방제 자료를 제공한다."
        best, scores = self._best_section(title, desc, "http://www.youngnong.co.kr/news/articleView.html?idxno=57763")
        self.assertEqual(best, "pest", msg=f"scores={scores}")

    def test_city_press_release_style_pest_issue_still_prefers_pest(self):
        title = "경남도, 과수화상병 확산 차단 위해 과원 예찰·약제 방제 총력"
        desc = "경남도는 시군과 합동으로 과원 전수조사와 정밀예찰을 실시하고 과수화상병 약제를 무상 공급한다고 보도자료를 통해 밝혔다."
        best, scores = self._best_section(title, desc, "https://www.gyeongnam.go.kr/board/view.gn?boardId=BBS_0000000")
        self.assertEqual(best, "pest", msg=f"scores={scores}")

    def test_policy_gate_does_not_drop_pest_execution_story(self):
        title = "진주시, 과수화상병 예방 교육·약제… 3회분 무상공급"
        desc = "진주시는 과수화상병 방제를 위해 382개 농가에 총 3회분의 약제를 무상으로 공급한다고 밝혔다."
        url = "https://www.newsis.com/view/NISX20260228_0003530198"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        self.assertTrue(main.is_relevant(title, desc, dom, url, self.conf["policy"], press))

    def test_seoul_city_agri_shipping_support_article_prefers_policy(self):
        title = "서울시가 전국 최초로 농산물 출하비용 보전하는 이유"
        desc = "서울시는 도매시장 출하 농산물의 경락가격 하락 시 출하비용을 보전하는 정책을 시행한다고 밝혔다."
        best, scores = self._best_section(title, desc, "https://biz.heraldcorp.com/article/10683302")
        self.assertEqual(best, "policy", msg=f"scores={scores}")

    def test_global_reassign_forces_policy_pest_context_to_pest(self):
        title = "진주시, 과수화상병 확산 차단 위해 과원 예찰·약제 방제 총력"
        desc = "진주시는 과수화상병 확산 차단을 위해 과원 정밀예찰과 약제 방제를 시행한다고 밝혔다."
        url = "https://www.newsis.com/view/NISX20260228_0003530198"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        a = main.Article(
            section="policy",
            title=title,
            description=desc,
            link=url,
            originallink=url,
            pub_dt_kst=self.now,
            domain=dom,
            press=press,
            norm_key=main.make_norm_key(main.canonicalize_url(url), press, main.norm_title_key(title)),
            title_key=main.norm_title_key(title),
            canon_url=main.canonicalize_url(url),
            topic=main.extract_topic(title, desc),
            score=main.compute_rank_score(title, desc, dom, self.now, self.conf["policy"], press),
        )
        by = {"policy": [a], "supply": [], "dist": [], "pest": []}
        moved = main._global_section_reassign(by, self.now, self.now)
        self.assertGreaterEqual(moved, 1)
        self.assertEqual(len(by["pest"]), 1)
        self.assertEqual(by["pest"][0].section, "pest")

    def test_policy_cleanup_moves_pest_context_to_pest_before_final_pick(self):
        title = "진주시, 과수화상병 확산 차단 위해 과원 예찰·약제 방제 총력"
        desc = "진주시는 과수화상병 확산 차단을 위해 과원 정밀예찰과 약제 방제를 시행한다고 밝혔다."
        url = "https://www.newsis.com/view/NISX20260228_0003530198"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        a = main.Article(
            section="policy",
            title=title,
            description=desc,
            link=url,
            originallink=url,
            pub_dt_kst=self.now,
            domain=dom,
            press=press,
            norm_key=main.make_norm_key(main.canonicalize_url(url), press, main.norm_title_key(title)),
            title_key=main.norm_title_key(title),
            canon_url=main.canonicalize_url(url),
            topic=main.extract_topic(title, desc),
            score=main.compute_rank_score(title, desc, dom, self.now, self.conf["policy"], press),
        )
        by = {"policy": [a], "supply": [], "dist": [], "pest": []}
        moved = main._enforce_pest_priority_over_policy(by)
        self.assertEqual(moved, 1)
        self.assertEqual(len(by["policy"]), 0)
        self.assertEqual(len(by["pest"]), 1)
        self.assertEqual(by["pest"][0].section, "pest")

    def test_policy_cleanup_boosts_and_keeps_pest_item(self):
        title = "경기도, 토마토 재배 농가 전수조사… 토마토뿔나방 방제 지원"
        desc = "경기도는 토마토뿔나방 확산 대응을 위해 재배 농가 전수조사를 실시하고 예찰·방제 자료를 제공한다."
        url = "http://www.youngnong.co.kr/news/articleView.html?idxno=57763"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        base_policy_score = main.compute_rank_score(title, desc, dom, self.now, self.conf["policy"], press)
        a = main.Article(
            section="policy",
            title=title,
            description=desc,
            link=url,
            originallink=url,
            pub_dt_kst=self.now,
            domain=dom,
            press=press,
            norm_key=main.make_norm_key(main.canonicalize_url(url), press, main.norm_title_key(title)),
            title_key=main.norm_title_key(title),
            canon_url=main.canonicalize_url(url),
            topic=main.extract_topic(title, desc),
            score=base_policy_score,
        )
        by = {"policy": [a], "supply": [], "dist": [], "pest": []}
        moved = main._enforce_pest_priority_over_policy(by)
        self.assertEqual(moved, 1)
        self.assertEqual(len(by["pest"]), 1)
        self.assertGreater(by["pest"][0].score, base_policy_score)

    def test_forced_pest_item_is_kept_in_final_selection(self):
        c = self.conf["pest"]
        # 일반 pest 고득점 기사
        u1 = "https://example.com/pest-high"
        t1 = "과수화상병 방제 총력"
        d1 = "과수화상병 예찰과 방제 약제 살포를 강화한다."
        p1 = "연합뉴스"
        a1 = main.Article(
            section="pest", title=t1, description=d1, link=u1, originallink=u1,
            domain=main.domain_of(u1), press=p1, pub_dt_kst=self.now,
            title_key=main.norm_title_key(t1), canon_url=main.canonicalize_url(u1),
            norm_key=main.make_norm_key(main.canonicalize_url(u1), p1, main.norm_title_key(t1)),
            topic=main.extract_topic(t1, d1),
            score=main.compute_rank_score(t1, d1, main.domain_of(u1), self.now, c, p1),
        )

        # policy->pest 강제 이동분(점수는 상대적으로 낮아도 forced_section으로 최종 유지)
        u2 = "https://example.com/pest-forced"
        t2 = "경기도, 토마토뿔나방 방제 지원"
        d2 = "토마토뿔나방 예찰·방제 지원을 실시한다."
        p2 = "뉴스1"
        a2 = main.Article(
            section="pest", title=t2, description=d2, link=u2, originallink=u2,
            domain=main.domain_of(u2), press=p2, pub_dt_kst=self.now,
            title_key=main.norm_title_key(t2), canon_url=main.canonicalize_url(u2),
            norm_key=main.make_norm_key(main.canonicalize_url(u2), p2, main.norm_title_key(t2)),
            topic=main.extract_topic(t2, d2),
            score=max(0.0, main.compute_rank_score(t2, d2, main.domain_of(u2), self.now, c, p2) - 5.0),
        )
        a2.forced_section = "pest"

        picked = main.select_top_articles([a1, a2], "pest", 1)
        self.assertTrue(any(x.link == u2 for x in picked), msg=str([(x.link, x.score) for x in picked]))

    def test_pest_execution_items_are_kept_even_without_forced_flag(self):
        c = self.conf["pest"]
        # 비실행형(상대 고점) 1건
        u1 = "https://example.com/pest-generic"
        t1 = "지역 병해충 대응 점검 회의"
        d1 = "병해충 관련 간담회와 회의가 열렸다."
        p1 = "연합뉴스"
        a1 = main.Article(
            section="pest", title=t1, description=d1, link=u1, originallink=u1,
            domain=main.domain_of(u1), press=p1, pub_dt_kst=self.now,
            title_key=main.norm_title_key(t1), canon_url=main.canonicalize_url(u1),
            norm_key=main.make_norm_key(main.canonicalize_url(u1), p1, main.norm_title_key(t1)),
            topic=main.extract_topic(t1, d1),
            score=20.0,
        )

        # 실행형 2건(요청 사례 패턴)
        u2 = "https://example.com/pest-fireblight"
        t2 = "진주시, 과수화상병 예방 교육·약제… 3회분 무상공급"
        d2 = "과수화상병 방제를 위해 농가에 약제를 무상 공급한다."
        p2 = "뉴시스"
        a2 = main.Article(
            section="pest", title=t2, description=d2, link=u2, originallink=u2,
            domain=main.domain_of(u2), press=p2, pub_dt_kst=self.now,
            title_key=main.norm_title_key(t2), canon_url=main.canonicalize_url(u2),
            norm_key=main.make_norm_key(main.canonicalize_url(u2), p2, main.norm_title_key(t2)),
            topic=main.extract_topic(t2, d2),
            score=8.0,
        )

        u3 = "https://example.com/pest-moth"
        t3 = "경기도, 토마토 재배 농가 전수조사… 토마토뿔나방 방제 지원"
        d3 = "토마토뿔나방 확산 대응을 위해 전수조사와 예찰·방제를 진행한다."
        p3 = "영농신문"
        a3 = main.Article(
            section="pest", title=t3, description=d3, link=u3, originallink=u3,
            domain=main.domain_of(u3), press=p3, pub_dt_kst=self.now,
            title_key=main.norm_title_key(t3), canon_url=main.canonicalize_url(u3),
            norm_key=main.make_norm_key(main.canonicalize_url(u3), p3, main.norm_title_key(t3)),
            topic=main.extract_topic(t3, d3),
            score=7.5,
        )

        picked = main.select_top_articles([a1, a2, a3], "pest", 2)
        picked_links = {x.link for x in picked}
        self.assertIn(u2, picked_links, msg=str([(x.link, x.score) for x in picked]))
        self.assertIn(u3, picked_links, msg=str([(x.link, x.score) for x in picked]))

    def test_pest_underfill_backfill_keeps_strong_focus_story_just_below_threshold(self):
        major1 = self._make_article(
            "pest",
            "경북, 사과 과수화상병 예찰 강화…농가 약제 살포 당부",
            "사과 과원 정밀예찰과 약제 살포를 통해 과수화상병 확산 차단에 나선다.",
            "https://www.yna.co.kr/view/AKR20260311000000061",
        )
        major2 = self._make_article(
            "pest",
            "전남도, 토마토뿔나방 방제 총력…재배농가 전수조사",
            "토마토뿔나방 확산 대응을 위해 전수조사와 정밀예찰을 실시한다.",
            "https://www.newsis.com/view/NISX20260311_0000000001",
        )
        backfill = self._make_article(
            "pest",
            "영월군, 과수화상병 예찰·약제 방제 총력",
            "과원 정밀예찰과 약제 방제를 동시에 진행해 확산 차단에 나선다.",
            "http://www.youngnong.co.kr/news/articleView.html?idxno=57763",
        )
        major1.score = 31.4
        major2.score = 29.8
        backfill.score = 22.5

        picked = main.select_top_articles([major1, major2, backfill], "pest", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(backfill.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_fishery_origin_label_story_is_filtered(self):
        title = "비싼 옥돔 사먹었는데 옥두어였다… 원산지 속인 제주업체 15곳 적발"
        desc = "외국산 수산물을 국내산으로 속여 판매한 사례가 확인됐다."
        url = "https://www.hani.co.kr/arti/area/jeju/1246935.html"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        for key, conf in self.conf.items():
            self.assertFalse(main.is_relevant(title, desc, dom, url, conf, press), msg=f"section={key}")

    def test_fishery_title_only_is_filtered_with_short_desc(self):
        title = "비싼 옥돔 사먹었는데 옥두어였다… 원산지 속인 제주업체 15곳 적발"
        # 설명이 짧아 fishery term이 제목 중심으로만 잡히는 경우도 차단되어야 함
        desc = "원산지 표시 위반 업체가 적발됐다."
        url = "https://www.hani.co.kr/arti/area/jeju/1246935.html"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        for key, conf in self.conf.items():
            self.assertFalse(main.is_relevant(title, desc, dom, url, conf, press), msg=f"section={key}")

    def test_pest_always_on_recall_queries_are_applied(self):
        section_conf = {
            "key": "pest",
            "queries": ["병해충 예찰 방제"],
            "must_terms": ["방제", "병해충", "약제", "예찰", "과수화상병", "토마토뿔나방"],
        }
        start_kst = main.dt_kst(main.date(2026, 3, 2), main.REPORT_HOUR_KST)
        end_kst = main.dt_kst(main.date(2026, 3, 3), main.REPORT_HOUR_KST)

        seen_queries = []
        old_func = main.naver_news_search_paged
        try:
            def _fake_search(q, display=50, pages=1, sort="date"):
                seen_queries.append(q)
                if "토마토뿔나방" in q:
                    return {
                        "items": [
                            {
                                "title": "경기도, 토마토 재배 농가 전수조사… 토마토뿔나방 방제 지원",
                                "description": "토마토뿔나방 확산 대응을 위해 예찰·방제를 지원한다.",
                                "link": "http://www.youngnong.co.kr/news/articleView.html?idxno=57763",
                                "originallink": "http://www.youngnong.co.kr/news/articleView.html?idxno=57763",
                                "pubDate": "Mon, 02 Mar 2026 00:30:00 +0000",
                            }
                        ]
                    }
                return {"items": []}

            main.naver_news_search_paged = _fake_search
            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_func

        self.assertTrue(any("토마토뿔나방" in q for q in seen_queries), msg=str(seen_queries))
        self.assertTrue(any("idxno=57763" in (a.link or "") for a in items), msg=str([(a.link, a.title) for a in items]))

    def test_pest_always_on_queries_also_try_page2_for_recall(self):
        section_conf = {
            "key": "pest",
            "queries": ["병해충 예찰 방제"],
            "must_terms": ["방제", "병해충", "약제", "예찰", "과수화상병", "토마토뿔나방"],
        }
        start_kst = main.dt_kst(main.date(2026, 3, 2), main.REPORT_HOUR_KST)
        end_kst = main.dt_kst(main.date(2026, 3, 3), main.REPORT_HOUR_KST)

        seen_page2 = []
        old_paged = main.naver_news_search_paged
        old_news = main.naver_news_search
        old_cond = main.COND_PAGING_ENABLED
        old_max_pages = main.COND_PAGING_MAX_PAGES
        old_cap = main.PEST_ALWAYS_ON_PAGE2_QUERY_CAP
        old_min_hours = main.WINDOW_MIN_HOURS
        try:
            main.COND_PAGING_ENABLED = True
            main.COND_PAGING_MAX_PAGES = 2
            main.PEST_ALWAYS_ON_PAGE2_QUERY_CAP = 2
            main.WINDOW_MIN_HOURS = 72

            def _fake_paged(q, display=50, pages=1, sort="date"):
                return {"items": []}

            def _fake_news(q, display=50, start=1, sort="date"):
                if start == 51 and ("과수화상병" in q):
                    seen_page2.append((q, start))
                    return {
                        "items": [
                            {
                                "title": "진주시, 과수화상병 예방 교육·약제… 3회분 무상공급",
                                "description": "진주시는 과수화상병 방제를 위해 약제를 무상 공급한다고 밝혔다.",
                                "link": "https://www.newsis.com/view/NISX20260228_0003530198",
                                "originallink": "https://www.newsis.com/view/NISX20260228_0003530198",
                                "pubDate": "Sat, 28 Feb 2026 15:00:00 +0000",
                            }
                        ]
                    }
                return {"items": []}

            main.naver_news_search_paged = _fake_paged
            main.naver_news_search = _fake_news
            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_paged
            main.naver_news_search = old_news
            main.COND_PAGING_ENABLED = old_cond
            main.COND_PAGING_MAX_PAGES = old_max_pages
            main.PEST_ALWAYS_ON_PAGE2_QUERY_CAP = old_cap
            main.WINDOW_MIN_HOURS = old_min_hours

        self.assertTrue(any(start == 51 for (_q, start) in seen_page2), msg=str(seen_page2))
        self.assertTrue(any("NISX20260228_0003530198" in (a.link or "") for a in items), msg=str([(a.link, a.title) for a in items]))

    def test_pest_page2_recall_runs_even_if_global_extra_budget_is_exhausted(self):
        section_conf = {
            "key": "pest",
            "queries": ["병해충 예찰 방제"],
            "must_terms": ["방제", "병해충", "약제", "예찰", "과수화상병", "토마토뿔나방"],
        }
        start_kst = main.dt_kst(main.date(2026, 3, 2), main.REPORT_HOUR_KST)
        end_kst = main.dt_kst(main.date(2026, 3, 3), main.REPORT_HOUR_KST)

        seen_page2 = []
        old_paged = main.naver_news_search_paged
        old_news = main.naver_news_search
        old_budget_fn = main._cond_paging_take_budget
        old_cond = main.COND_PAGING_ENABLED
        old_max_pages = main.COND_PAGING_MAX_PAGES
        old_cap = main.PEST_ALWAYS_ON_PAGE2_QUERY_CAP
        old_min_hours = main.WINDOW_MIN_HOURS
        try:
            main.COND_PAGING_ENABLED = True
            main.COND_PAGING_MAX_PAGES = 2
            main.PEST_ALWAYS_ON_PAGE2_QUERY_CAP = 1
            main._cond_paging_take_budget = lambda n=1: False
            main.WINDOW_MIN_HOURS = 72

            def _fake_paged(q, display=50, pages=1, sort="date"):
                return {"items": []}

            def _fake_news(q, display=50, start=1, sort="date"):
                if start == 51:
                    seen_page2.append((q, start))
                    return {
                        "items": [
                            {
                                "title": "진주시, 과수화상병 예방 교육·약제… 3회분 무상공급",
                                "description": "진주시는 과수화상병 방제를 위해 약제를 무상 공급한다고 밝혔다.",
                                "link": "https://www.newsis.com/view/NISX20260228_0003530198",
                                "originallink": "https://www.newsis.com/view/NISX20260228_0003530198",
                                "pubDate": "Sat, 28 Feb 2026 15:00:00 +0000",
                            }
                        ]
                    }
                return {"items": []}

            main.naver_news_search_paged = _fake_paged
            main.naver_news_search = _fake_news
            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_paged
            main.naver_news_search = old_news
            main._cond_paging_take_budget = old_budget_fn
            main.COND_PAGING_ENABLED = old_cond
            main.COND_PAGING_MAX_PAGES = old_max_pages
            main.PEST_ALWAYS_ON_PAGE2_QUERY_CAP = old_cap
            main.WINDOW_MIN_HOURS = old_min_hours

        self.assertTrue(any(start == 51 for (_q, start) in seen_page2), msg=str(seen_page2))
        self.assertTrue(any("NISX20260228_0003530198" in (a.link or "") for a in items), msg=str([(a.link, a.title) for a in items]))

    def test_pest_web_recall_collects_when_news_search_misses(self):
        section_conf = {
            "key": "pest",
            "queries": ["병해충 예찰 방제"],
            "must_terms": ["방제", "병해충", "약제", "예찰", "과수화상병", "토마토뿔나방"],
        }
        start_kst = main.dt_kst(main.date(2026, 3, 2), main.REPORT_HOUR_KST)
        end_kst = main.dt_kst(main.date(2026, 3, 3), main.REPORT_HOUR_KST)

        old_paged = main.naver_news_search_paged
        old_web = main.naver_web_search
        old_pub = main._best_effort_article_pubdate_kst
        old_enabled = main.PEST_WEB_RECALL_ENABLED
        old_cap = main.PEST_WEB_RECALL_QUERY_CAP
        old_min_hours = main.WINDOW_MIN_HOURS
        try:
            main.PEST_WEB_RECALL_ENABLED = True
            main.PEST_WEB_RECALL_QUERY_CAP = 2
            main.WINDOW_MIN_HOURS = 72

            def _fake_paged(q, display=50, pages=1, sort="date"):
                return {"items": []}

            def _fake_web(q, display=10, start=1, sort="date"):
                if "과수화상병" in q:
                    return {
                        "items": [
                            {
                                "title": "진주시, 과수화상병 예방 교육·약제… 3회분 무상공급",
                                "description": "진주시는 과수화상병 방제를 위해 약제를 무상 공급한다고 밝혔다.",
                                "link": "https://www.newsis.com/view/NISX20260228_0003530198",
                            }
                        ]
                    }
                return {"items": []}

            def _fake_pub(url):
                if "NISX20260228_0003530198" in (url or ""):
                    return datetime(2026, 3, 1, 0, 0, tzinfo=main.KST)
                return None

            main.naver_news_search_paged = _fake_paged
            main.naver_web_search = _fake_web
            main._best_effort_article_pubdate_kst = _fake_pub

            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_paged
            main.naver_web_search = old_web
            main._best_effort_article_pubdate_kst = old_pub
            main.PEST_WEB_RECALL_ENABLED = old_enabled
            main.PEST_WEB_RECALL_QUERY_CAP = old_cap
            main.WINDOW_MIN_HOURS = old_min_hours

        self.assertTrue(any("NISX20260228_0003530198" in (a.link or "") for a in items), msg=str([(a.link, a.title) for a in items]))

    def test_collect_candidates_does_not_extend_window_by_default(self):
        section_conf = {
            "key": "pest",
            "queries": ["과수화상병 방제"],
            "must_terms": ["방제", "병해충", "약제", "예찰", "과수화상병"],
        }

        # 기본 정책은 윈도우 확장 없음(24h/영업일 윈도우 준수)
        # -> 시작 시각보다 이른 기사는 제외되어야 한다.
        end_kst = main.dt_kst(main.date(2026, 3, 3), main.REPORT_HOUR_KST)
        start_kst = main.dt_kst(main.date(2026, 3, 2), main.REPORT_HOUR_KST)

        old_func = main.naver_news_search_paged
        try:
            def _fake_search(q, display=50, pages=1, sort="date"):
                return {
                    "items": [
                        {
                            "title": "진주시, 과수화상병 예방 교육·약제… 3회분 무상공급",
                            "description": "진주시는 과수화상병 방제를 위해 약제를 무상 공급한다고 밝혔다.",
                            "link": "https://www.newsis.com/view/NISX20260228_0003530198",
                            "originallink": "https://www.newsis.com/view/NISX20260228_0003530198",
                            # 2026-03-01 00:00 KST
                            "pubDate": "Sat, 28 Feb 2026 15:00:00 +0000",
                        }
                    ]
                }

            main.naver_news_search_paged = _fake_search
            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_func

        self.assertFalse(any("NISX20260228_0003530198" in (a.link or "") for a in items), msg=str([(a.link, a.pub_dt_kst) for a in items]))

    def test_collect_candidates_window_min_hours_can_be_opted_in(self):
        section_conf = {
            "key": "pest",
            "queries": ["과수화상병 방제"],
            "must_terms": ["방제", "병해충", "약제", "예찰", "과수화상병"],
        }

        end_kst = main.dt_kst(main.date(2026, 3, 3), main.REPORT_HOUR_KST)
        start_kst = main.dt_kst(main.date(2026, 3, 2), main.REPORT_HOUR_KST)

        old_func = main.naver_news_search_paged
        old_min_hours = main.WINDOW_MIN_HOURS
        try:
            main.WINDOW_MIN_HOURS = 72

            def _fake_search(q, display=50, pages=1, sort="date"):
                return {
                    "items": [
                        {
                            "title": "진주시, 과수화상병 예방 교육·약제… 3회분 무상공급",
                            "description": "진주시는 과수화상병 방제를 위해 약제를 무상 공급한다고 밝혔다.",
                            "link": "https://www.newsis.com/view/NISX20260228_0003530198",
                            "originallink": "https://www.newsis.com/view/NISX20260228_0003530198",
                            "pubDate": "Sat, 28 Feb 2026 15:00:00 +0000",
                        }
                    ]
                }

            main.naver_news_search_paged = _fake_search
            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_func
            main.WINDOW_MIN_HOURS = old_min_hours

        self.assertTrue(any("NISX20260228_0003530198" in (a.link or "") for a in items), msg=str([(a.link, a.pub_dt_kst) for a in items]))


    def test_distribution_issue_prefers_dist_over_policy(self):
        title = "가락시장 하역 중단 장기화…출하 농민 피해 확산"
        desc = "가락시장 도매시장 하역대란이 장기화되며 반입 차질과 경락 지연이 이어져 산지 농가 피해가 커지고 있다."
        best, scores = self._best_section(title, desc, "https://www.nongmin.com/article/20260304500375")
        self.assertEqual(best, "dist", msg=f"scores={scores}")

    def test_local_agri_program_issue_prefers_policy(self):
        title = "지자체, 농산물 수급안정 지원 조례 개정…직불금·농민수당 연계"
        desc = "지자체가 농산물 수급안정을 위해 직불금과 농민수당을 연계하는 정책을 발표하고 예산 확대를 추진한다."
        best, scores = self._best_section(title, desc, "https://www.amnews.co.kr/news/articleView.html?idxno=71319")
        self.assertEqual(best, "policy", msg=f"scores={scores}")

    def test_market_disruption_story_is_not_relevant_to_policy(self):
        title = "가락·구리 시장 동시휴업…딸기 산지 폐기량 2배 늘고 경락값 ‘뚝’"
        desc = "가락시장과 구리시장이 동시에 휴업하면서 딸기 가격과 출하량이 크게 흔들렸다는 현장 기사다."
        url = "https://www.nongmin.com/article/20260309500761"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        self.assertFalse(main.is_relevant(title, desc, dom, url, self.conf["policy"], press))
        best, scores = self._best_section(title, desc, url)
        self.assertEqual(best, "dist", msg=f"scores={scores}")

    def test_policy_general_macro_tail_is_rejected_without_agri_focus(self):
        title = "수출·물가 등 경제 ‘빨간불’…부·울·경 긴급 대응"
        desc = "부산 울산 경남이 유가와 물가 상승 대응에 나섰고 농업용 면세유 지원이 일부 포함됐다는 종합 경제 기사다."
        url = "https://biz.heraldcorp.com/article/10691114"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        self.assertFalse(main.is_relevant(title, desc, dom, url, self.conf["policy"], press))

    def test_global_reassign_moves_dist_fit_dominant_item_to_dist(self):
        title = "가락시장 하역 중단 장기화…출하 농민 피해 확산"
        desc = "가락시장 도매시장 하역대란이 장기화되며 반입 차질과 경락 지연이 이어져 산지 농가 피해가 커지고 있다."
        url = "https://www.nongmin.com/article/20260304500375"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        a = main.Article(
            section="policy",
            title=title,
            description=desc,
            link=url,
            originallink=url,
            pub_dt_kst=self.now,
            domain=dom,
            press=press,
            norm_key=main.make_norm_key(main.canonicalize_url(url), press, main.norm_title_key(title)),
            title_key=main.norm_title_key(title),
            canon_url=main.canonicalize_url(url),
            topic=main.extract_topic(title, desc),
            score=main.compute_rank_score(title, desc, dom, self.now, self.conf["policy"], press),
        )
        by = {"policy": [a], "supply": [], "dist": [], "pest": []}
        moved = main._global_section_reassign(by, self.now, self.now)
        self.assertGreaterEqual(moved, 1)
        self.assertEqual(len(by["dist"]), 1)
        self.assertEqual(by["dist"][0].section, "dist")
    def test_supply_core_prefers_commodity_topic_over_policy_topic(self):
        now = self.now
        c = self.conf["supply"]

        # 정책 토픽으로 추출되는 기사
        u1 = "https://www.agrinet.co.kr/news/articleView.html?idxno=402094"
        t1 = "봄동값, '비빔밥 특수'로 반짝 상승…출하 막바지 내림세"
        d1 = "봄동값은 비빔밥 특수로 반짝 상승했으나 고추 반입량 증가로 시세가 하락했다."
        p1 = main.normalize_press_label(main.press_name_from_url(u1), u1)
        a1 = main.Article(
            section="supply", title=t1, description=d1, link=u1, originallink=u1,
            domain=main.domain_of(u1), press=p1, pub_dt_kst=now,
            title_key=main.norm_title_key(t1), canon_url=main.canonicalize_url(u1),
            norm_key=main.make_norm_key(main.canonicalize_url(u1), p1, main.norm_title_key(t1)),
            topic=main.extract_topic(t1, d1),
            score=main.compute_rank_score(t1, d1, main.domain_of(u1), now, c, p1),
        )

        # 품목 토픽 기사
        u2 = "http://www.aflnews.co.kr/news/articleView.html?idxno=315415"
        t2 = "명절 특수 끝난 과일, 가격 하락세"
        d2 = "사과와 배, 천혜향·레드향, 딸기·참외 등 과채류 가격이 하락세다."
        p2 = main.normalize_press_label(main.press_name_from_url(u2), u2)
        a2 = main.Article(
            section="supply", title=t2, description=d2, link=u2, originallink=u2,
            domain=main.domain_of(u2), press=p2, pub_dt_kst=now,
            title_key=main.norm_title_key(t2), canon_url=main.canonicalize_url(u2),
            norm_key=main.make_norm_key(main.canonicalize_url(u2), p2, main.norm_title_key(t2)),
            topic=main.extract_topic(t2, d2),
            score=main.compute_rank_score(t2, d2, main.domain_of(u2), now, c, p2),
        )

        picked = main.select_top_articles([a1, a2], "supply", 5)
        core = [a for a in picked if getattr(a, "is_core", False)]
        self.assertTrue(any(a.link == u2 for a in core), msg=str([(x.link, x.topic, x.is_core) for x in picked]))
        self.assertFalse(any(a.link == u1 for a in core), msg=str([(x.link, x.topic, x.is_core) for x in picked]))


    def test_supply_event_dedupe_collapses_similar_flower_cost_story(self):
        url1 = "https://www.ytn.co.kr/_ln/0103_202603071412402937"
        url2 = "https://www.ytn.co.kr/_ln/0103_202603072211289925"
        a1 = self._make_article(
            "supply",
            "유가 급등에 난방비도 치솟아... 화훼 농가 '울상'",
            "유가 급등으로 화훼 농가들이 심각한 경제적 타격을 받고 있다. 해외에서 수입되는 원예용 상토의 운송비 증가가 추가적인 부담을 주고 있다.",
            url1,
        )
        a2 = self._make_article(
            "supply",
            "유가 급등에 꽃샘추위까지...한숨 깊어가는 화훼 농가",
            "유가 상승과 꽃샘추위로 화훼 농가의 상황이 더욱 악화되고 있다. 원예용 상토 가격 인상이 농가에 큰 영향을 미치고 있어 우려가 커지고 있다.",
            url2,
        )

        self.assertEqual(main._event_key(a1, "supply"), main._event_key(a2, "supply"))
        picked = main.select_top_articles([a1, a2], "supply", 5)
        picked_urls = {a.link for a in picked}
        self.assertEqual(len(picked_urls & {url1, url2}), 1, msg=str([(x.link, x.score) for x in picked]))

    def test_supply_event_dedupe_collapses_similar_grape_fuel_story(self):
        url1 = "https://www.ytn.co.kr/_ln/0115_202603121048360743"
        url2 = "https://www.ytn.co.kr/_ln/0115_202603121445460543"
        a1 = self._make_article(
            "supply",
            "고유가에 포도 농가 '비상'...기름보일러 가구도 걱정",
            "국제유가 상승 여파로 포도 농가의 난방비 부담이 커졌다. 기름보일러를 쓰는 농가들은 비상이라고 호소했다.",
            url1,
        )
        a2 = self._make_article(
            "supply",
            "고유가에 포도 농가 '비상'...면세 등유 가격 올라",
            "유가 상승으로 면세 등유 가격이 오르면서 하우스 포도 농가의 연료비 부담이 커졌다. 난방비 비상이라는 현장 목소리가 나온다.",
            url2,
        )

        self.assertEqual(main._event_key(a1, "supply"), main._event_key(a2, "supply"))
        picked = main.select_top_articles([a1, a2], "supply", 5)
        picked_urls = {a.link for a in picked}
        self.assertEqual(len(picked_urls & {url1, url2}), 1, msg=str([(x.link, x.score) for x in picked]))

    def test_local_coop_export_feature_is_not_forced_into_dist(self):
        title = "경주 현곡농협, 수출 등 활발한 경제사업으로 농가실익 증진"
        desc = "경주 현곡농협이 샤인머스캣 농가의 수출을 통해 경제적 실익을 증진하고 있다. 대만으로의 수출이 예정되어 있으며, GAP 인증을 받은 농가들이 참여하고 있다."
        best, scores = self._best_section(title, desc, "https://www.nongmin.com/article/20260306500345")
        self.assertNotEqual(best, "dist", msg=f"scores={scores}")

    def test_macro_price_article_prefers_policy_over_supply(self):
        title = "2월 물가 2.0% 올랐지만 축산물 6.0% 오르며 '들썩'… 이란 사태 반영..."
        desc = "2월 물가가 2.0% 상승했지만, 축산물은 6.0% 급등하며 시장이 불안정해지고 있다. 농식품부는 쌀과 사과의 공급을 조절해 안정화를 도모할 계획이다."
        best, scores = self._best_section(title, desc, "https://www.segye.com/newsView/20260306506243")
        self.assertEqual(best, "policy", msg=f"scores={scores}")

    def test_local_smart_agri_zone_selection_is_not_dist_core(self):
        herald = self._make_article(
            "dist",
            "의성군, 2026년 노지 스마트농업 육성지구 최종 선정",
            "의성군이 2026년 노지 스마트농업 육성지구로 선정되어 기반 시설 확충을 목표로 하고 있다. 스마트 농산물산지유통센터도 연계하여 발전할 계획이다.",
            "https://biz.heraldcorp.com/article/10688433",
        )
        strong = self._make_article(
            "dist",
            "가락시장 하역 중단 위기 물류 차질 비상",
            "가락시장 청과 반입이 흔들리며 경매 일정과 유통 물량 조정에 비상이 걸렸다.",
            "https://www.nongmin.com/article/20260304500375",
        )

        picked = main.select_top_articles([strong, herald], "dist", 5)
        herald_picked = next((x for x in picked if x.link == herald.link), None)
        self.assertTrue(herald_picked is None or (not getattr(herald_picked, "is_core", False)), msg=str([(x.link, x.score, x.is_core) for x in picked]))


    def test_sedaily_price_watch_prefers_policy_over_supply(self):
        title = "“주말에 고기 좀 구워볼까?” 했다가 ‘깜짝’…소·돼지고기 가격 두..."
        desc = "ASF 발생으로 인해 돼지고기 출하가 지연되며 가격이 급등하고 있다. 또한, 사과 가격도 환율 상승으로 인해 상승세를 보이고 있다."
        best, scores = self._best_section(title, desc, "https://www.sedaily.com/article/20016226")
        self.assertEqual(best, "policy", msg=f"scores={scores}")

    def test_sedaily_strawberry_growth_story_prefers_supply(self):
        title = "온종일 불때야 하는데 막막 초록색 딸기 바라보며 한숨"
        desc = "딸기 체험 농장을 운영하는 농가가 생육적온과 난방비 부담을 호소했다."
        best, scores = self._best_section(title, desc, "https://www.sedaily.com/article/20017059")
        self.assertEqual(best, "supply", msg=f"scores={scores}")

    def test_seoul_citrus_org_promo_story_prefers_supply(self):
        title = "(사)제주감귤연합회, 한국민속촌서 ‘제주 만감류’ 진수 선보여…수도권 나들이객 집중 홍보"
        desc = "제철 제주 만감류 강점 홍보. 향·당도·식감이 뛰어난 천혜향과 레드향 등 주요 출하 시기 만감류를 소개하며 소비자 접점을 넓혔다."
        best, scores = self._best_section(title, desc, "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500177?wlog_tag3=naver")
        self.assertEqual(best, "supply", msg=f"scores={scores}")

    def test_fnnews_citrus_blind_test_story_prefers_supply(self):
        title = "제주 감귤, 수입산과 맛 블라인드 테스트 69% 압도"
        desc = "제주산 만감류 천혜향이 수입 만다린보다 두 배 이상 높은 소비자 선호도를 기록하며 제주 감귤의 품질 경쟁력을 입증했다."
        best, scores = self._best_section(title, desc, "https://www.fnnews.com/news/202603091837432209")
        self.assertEqual(best, "supply", msg=f"scores={scores}")

    def test_mt_imported_egg_supply_stabilization_story_prefers_policy(self):
        title = "다음주 美 신선란 112만개 공급…홈플러스·메가마트서 한판 5790원"
        desc = "정부가 수입 신선란 물량을 공급해 홈플러스와 메가마트에서 한 판 5790원에 판매하는 수급 안정 조치를 추진한다."
        best, scores = self._best_section(title, desc, "https://www.mt.co.kr/economy/2026/03/09/2026030917232924524")
        self.assertEqual(best, "policy", msg=f"scores={scores}")

    def test_mt_apology_sagwa_politics_story_is_excluded(self):
        title = "한병도 \"尹 반대 결의문, 반쪽짜리 사과 …장동혁 입장 밝혀라\""
        desc = "더불어민주당 원내대표 한병도는 정치 복귀에 반대하며 장동혁의 입장을 요구했다. 그는 중동사태에 대한 경제대응 TF를 출범했다고 발표했다."
        best, scores = self._best_section(title, desc, "https://www.mt.co.kr/politics/2026/03/10/2026031009405991292")
        self.assertIsNone(best, msg=f"scores={scores}")

    def test_nongmin_strawberry_export_shipping_story_prefers_dist(self):
        title = "‘굿뜨래 싱싱 딸기 ’ 몽골행…1t 선적"
        desc = "부여 서부여농협은 국내 딸기 가격 변동에 대응하기 위해 1t의 ‘굿뜨래 싱싱 딸기’를 몽골로 수출했다. 이는 농가 소득 증대에 도움을 주려는 노력의 일환이다."
        best, scores = self._best_section(title, desc, "https://www.nongmin.com/article/20260309500740")
        self.assertEqual(best, "dist", msg=f"scores={scores}")

    def test_nocut_policy_market_brief_prefers_policy(self):
        title = "농축산물 가격 대체로 하락세…중동 전쟁에 따른 농산물 수급 영향 '제한적'"
        desc = "최근 중동 전쟁으로 인해 기름값이 상승하고 있는 가운데 단기적인 농산물 수급 영향은 제한적일 것으로 분석됐다. 과일류도 대체로 전년 대비 낮은 수준이지만 사과는 2025년산 생산량 감소로 가격이 다소 높은 수준이며 3월 정부 가용물량을 도매시장에 분산 출하할 계획이다."
        best, scores = self._best_section(title, desc, "https://www.nocutnews.co.kr/news/6481885")
        self.assertEqual(best, "policy", msg=f"scores={scores}")

    def test_supply_selection_excludes_policy_market_brief_story(self):
        cabbage = self._make_article(
            "supply",
            "저장 배추 물량 감소…시세 상승 기대",
            "배추 저장 물량이 줄며 도매시장 시세 상승이 예상된다.",
            "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500277?wlog_tag3=naver",
        )
        strawberry = self._make_article(
            "supply",
            "온종일 불때야 하는데 막막 초록색 딸기 바라보며 한숨",
            "딸기 체험 농장을 운영하는 농가가 생육적온과 난방비 부담을 호소했다.",
            "https://www.sedaily.com/article/20017059",
        )
        citrus = self._make_article(
            "supply",
            "제주 감귤, 수입산과 맛 블라인드 테스트 69% 압도",
            "제주산 만감류 천혜향이 수입 만다린보다 두 배 이상 높은 소비자 선호도를 기록했다.",
            "https://www.fnnews.com/news/202603091837432209",
        )
        policy_brief = self._make_article(
            "supply",
            "농축산물 가격 대체로 하락세…중동 전쟁에 따른 농산물 수급 영향 '제한적'",
            "최근 중동 전쟁으로 인해 기름값이 상승하고 있는 가운데 단기적인 농산물 수급 영향은 제한적일 것으로 분석됐다. 과일류도 대체로 전년 대비 낮은 수준이지만 사과는 2025년산 생산량 감소로 가격이 다소 높은 수준이며 3월 정부 가용물량을 도매시장에 분산 출하할 계획이다.",
            "https://www.nocutnews.co.kr/news/6481885",
        )
        cabbage.score = 29.4
        strawberry.score = 28.7
        citrus.score = 27.9
        policy_brief.score = 31.5
        picked = main.select_top_articles([cabbage, strawberry, citrus, policy_brief], "supply", 5)
        picked_urls = {a.link for a in picked}
        self.assertNotIn(policy_brief.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))

    def test_supply_selection_excludes_dist_export_shipping_story(self):
        cabbage = self._make_article(
            "supply",
            "저장 배추 물량 감소…시세 상승 기대",
            "배추 저장 물량이 줄며 도매시장 시세 상승이 예상된다.",
            "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500277?wlog_tag3=naver",
        )
        strawberry = self._make_article(
            "supply",
            "온종일 불때야 하는데 막막 초록색 딸기 바라보며 한숨",
            "딸기 체험 농장을 운영하는 농가가 생육적온과 난방비 부담을 호소했다.",
            "https://www.sedaily.com/article/20017059",
        )
        citrus = self._make_article(
            "supply",
            "제주 감귤, 수입산과 맛 블라인드 테스트 69% 압도",
            "제주산 만감류 천혜향이 수입 만다린보다 두 배 이상 높은 소비자 선호도를 기록했다.",
            "https://www.fnnews.com/news/202603091837432209",
        )
        export_story = self._make_article(
            "supply",
            "‘굿뜨래 싱싱 딸기 ’ 몽골행…1t 선적",
            "부여 서부여농협은 국내 딸기 가격 변동에 대응하기 위해 1t의 ‘굿뜨래 싱싱 딸기’를 몽골로 수출했다. 이는 농가 소득 증대에 도움을 주려는 노력의 일환이다.",
            "https://www.nongmin.com/article/20260309500740",
        )
        cabbage.score = 29.4
        strawberry.score = 28.7
        citrus.score = 27.9
        export_story.score = 30.5
        picked = main.select_top_articles([cabbage, strawberry, citrus, export_story], "supply", 5)
        picked_urls = {a.link for a in picked}
        self.assertNotIn(export_story.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))
        self.assertIn(strawberry.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))

    def test_supply_selection_prefers_distinct_feature_topics_over_policy_stabilization_or_repeat_feature(self):
        cabbage = self._make_article(
            "supply",
            "대아청과 “2026년산 저장 배추 5.2% 줄었지만, 상품성 우수…시세 상승 기대”",
            "대아청과는 2026년산 저장 배추가 지난해보다 5.2% 감소했으나, 우수한 상품성으로 시세 상승이 기대된다고 발표했다.",
            "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500277?wlog_tag3=naver",
        )
        flower1 = self._make_article(
            "supply",
            "“꽃값 그대로인데 한 달 난방비만 1000만 원” 치솟은 유가에 화훼 업계 울상",
            "화훼 업계는 유가 상승으로 난방비가 급증해 어려움을 겪고 있으며, 한 달에 1000만 원에 달하는 난방비를 부담하고 있다.",
            "https://www.sedaily.com/article/20016961",
        )
        flower2 = self._make_article(
            "supply",
            "“울며 겨자먹기로 버티죠” 중동발 기름값 급등에 농민들 울상",
            "중동발 기름값 급등은 농민과 화훼 업계에 큰 타격을 주고 있다. 도매상에서 나무를 사는 비용 상승으로 꽃 소비도 줄어드는 상황이다.",
            "https://www.sedaily.com/article/20017109",
        )
        strawberry = self._make_article(
            "supply",
            "“온종일 불때야 하는데 막막” 초록색 딸기 바라보며 한숨",
            "딸기 체험 농장을 운영하는 농가가 생육적온을 맞추기 어려워 난방 부담이 커졌고 초록빛 딸기가 그대로 남아 있다고 설명했다.",
            "https://www.sedaily.com/article/20017059",
        )
        citrus = self._make_article(
            "supply",
            "제주 감귤, 수입산과 맛 블라인드 테스트 69% 압도",
            "제주산 만감류 천혜향이 수입 만다린보다 두 배 이상 높은 소비자 선호도를 기록하며 제주 감귤의 품질 경쟁력을 입증했다.",
            "https://www.fnnews.com/news/202603091837432209",
        )
        egg = self._make_article(
            "supply",
            "다음주 美 신선란 112만개 공급…홈플러스·메가마트서 한판 5790원",
            "정부가 수입 신선란 물량을 공급해 홈플러스와 메가마트에서 한 판 5790원에 판매하는 수급 안정 조치를 추진한다.",
            "https://www.mt.co.kr/economy/2026/03/09/2026030917232924524",
        )
        picked = main.select_top_articles([cabbage, flower1, flower2, strawberry, citrus, egg], "supply", 5)
        picked_urls = {a.link for a in picked}
        self.assertIn(strawberry.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))
        self.assertIn(citrus.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))
        self.assertNotIn(egg.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))
        self.assertEqual(len(picked_urls & {flower1.link, flower2.link}), 1, msg=str([(x.link, x.score, x.topic) for x in picked]))


    def test_supply_weak_tail_context_keeps_promo_but_flags_official_visit_stories(self):
        citrus_title = "(사)제주감귤연합회, 한국민속촌서 ‘제주 만감류’ 진수 선보여…수도권 나들이객 집중 홍보"
        citrus_desc = "제철 제주 만감류 강점 홍보. 향·당도·식감이 뛰어난 천혜향과 레드향 등 주요 출하 시기 만감류를 소개하며 소비자 접점을 넓혔다."
        watermelon_title = "최경주 전북농업기술원장, 지역 명품 초당옥수수·수박 현장 찾아 격려"
        watermelon_desc = "본격 출하를 앞둔 수박 농가 현장을 찾아 생육 상황을 살피고 농가 애로를 청취했다."
        self.assertFalse(main.is_supply_weak_tail_context(citrus_title, citrus_desc))
        self.assertTrue(main.is_supply_weak_tail_context(watermelon_title, watermelon_desc))

    def test_supply_selection_keeps_target_feature_stories_and_excludes_visit_tail(self):
        cabbage = self._make_article(
            "supply",
            "서울가락시장 배추 반입량 감소로 시세 강세",
            "배추 반입량이 줄고 도매시장 시세가 오름세를 보였다.",
            "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500277?wlog_tag3=naver",
        )
        flower = self._make_article(
            "supply",
            "유가가 그대로인데도 난방비만 1000만원…화훼 농가 비상",
            "화훼 농가가 난방비 부담으로 생육 관리에 어려움을 겪고 있다.",
            "https://www.sedaily.com/article/20016961",
        )
        market = self._make_article(
            "supply",
            "배추 7만천톤 평년보다 9.4% 감소",
            "가락시장 배추 공급 감소가 배추 수급과 가격 흐름에 영향을 주고 있다.",
            "http://www.newsfarm.co.kr/news/articleView.html?idxno=100475",
        )
        strawberry = self._make_article(
            "supply",
            "출하철 불안한데 짙은 초록빛 딸기 바라보는 시선",
            "딸기 체험 농장을 운영하는 농가가 생육적온과 난방비 부담을 호소했다.",
            "https://www.sedaily.com/article/20017059",
        )
        citrus_promo = self._make_article(
            "supply",
            "(사)제주감귤연합회, 한국민속촌서 ‘제주 만감류’ 진수 선보여…수도권 나들이객 집중 홍보",
            "제철 제주 만감류 강점 홍보. 향·당도·식감이 뛰어난 천혜향과 레드향 등 주요 출하 시기 만감류를 소개하며 소비자 접점을 넓혔다.",
            "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500177?wlog_tag3=naver",
        )
        watermelon_visit = self._make_article(
            "supply",
            "최경주 전북농업기술원장, 지역 명품 초당옥수수·수박 현장 찾아 격려",
            "수박 농가 현장을 찾아 생육 상황을 살피고 농가 애로를 청취했다.",
            "http://www.nongup.net/news/articleView.html?idxno=32597",
        )
        nocut_policy = self._make_article(
            "supply",
            "농축산물 가격 대체로 하락세…중동 전쟁에 따른 농산물 수급 영향 '제한적'",
            "중동 전쟁 여파에도 농산물 수급 영향은 제한적이라는 농식품부 점검 결과가 나왔다.",
            "https://www.nocutnews.co.kr/news/6481885",
        )
        cabbage.score = 29.4
        flower.score = 28.5
        market.score = 27.6
        strawberry.score = 27.9
        citrus_promo.score = 28.9
        watermelon_visit.score = 28.3
        nocut_policy.score = 29.2
        picked = main.select_top_articles(
            [cabbage, flower, market, strawberry, citrus_promo, watermelon_visit, nocut_policy],
            "supply",
            5,
        )
        picked_urls = {a.link for a in picked}
        self.assertIn(strawberry.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))
        self.assertIn(citrus_promo.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))
        self.assertNotIn(watermelon_visit.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))
        self.assertNotIn(nocut_policy.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))

    def test_supply_event_key_dedupes_same_citrus_quality_compare_story(self):
        citrus1 = self._make_article(
            "supply",
            "제주 감귤, 수입산과 맛 블라인드 테스트 69% 압도",
            "제주산 만감류 천혜향이 수입 만다린보다 두 배 이상 높은 소비자 선호도를 기록하며 제주 감귤의 품질 경쟁력을 입증했다.",
            "https://www.fnnews.com/news/202603091837432209",
        )
        citrus2 = self._make_article(
            "supply",
            "제주감귤연합회 ""천혜향, 수입 만다린보다 선호도 2배""",
            "제주감귤연합회는 제주산 천혜향이 수입 만다린과의 블라인드 비교에서 더 높은 선호도와 품질 경쟁력을 보였다고 밝혔다.",
            "https://www.newsis.com/view/NISX20260309_0003999999",
        )
        deduped = main._dedupe_by_event_key([citrus1, citrus2], "supply")
        self.assertEqual(len(deduped), 1, msg=str([(x.link, x.topic, main._event_key(x, "supply")) for x in deduped]))


    def test_supply_event_key_dedupes_same_citrus_org_promo_story(self):
        citrus1 = self._make_article(
            "supply",
            "(사)제주감귤연합회, 한국민속촌서 ‘제주 만감류’ 진수 선보여…수도권 공략",
            "(사)제주감귤연합회는 제주산 만감류의 대표 제품인 한라봉과 천혜향의 출하 시기를 홍보하며 수도권 소비자 접점을 넓힌다고 밝혔다.",
            "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500177?wlog_tag3=naver",
        )
        citrus2 = self._make_article(
            "supply",
            "제주감귤연합회, 한국민속촌서 한라봉·천혜향 제철 홍보…‘기다리던 봄맛’",
            "제주감귤연합회는 한국민속촌에서 한라봉과 천혜향을 소개하며 제철 홍보에 나섰다고 밝혔다.",
            "https://www.segye.com/newsView/20260309515742",
        )
        deduped = main._dedupe_by_event_key([citrus1, citrus2], "supply")
        self.assertEqual(len(deduped), 1, msg=str([(x.link, x.topic, main._event_key(x, "supply")) for x in deduped]))


    def test_dist_event_key_dedupes_same_local_org_feature_story(self):
        coop1 = self._make_article(
            "dist",
            "경주 현곡농협, 샤인머스캣 수출 확대… 경제사업 성과",
            "현곡농협은 샤인머스캣 공동선별과 수출 판로 확대를 통해 농가실익 증진과 브랜드 성과를 냈다고 밝혔다.",
            "https://www.nongmin.com/article/20260310500111",
        )
        coop2 = self._make_article(
            "dist",
            "현곡농협, 샤인머스캣 수출 판로 넓혀 농가실익 증진",
            "현곡농협은 샤인머스캣 수출, 공동선별, 브랜드 전략으로 농가실익과 경제사업 성과를 높였다고 밝혔다.",
            "https://www.agrinet.co.kr/news/articleView.html?idxno=400001",
        )
        deduped = main._dedupe_by_event_key([coop1, coop2], "dist")
        self.assertEqual(len(deduped), 1, msg=str([(x.link, x.topic, main._event_key(x, "dist")) for x in deduped]))


    def test_policy_event_key_prefers_official_source_for_same_announcement(self):
        official = self._make_article(
            "policy",
            "농식품부, 사과·배 할인 지원 확대… 성수품 수급안정 추진",
            "농식품부는 사과와 배의 할인 지원을 확대하고 성수품 공급과 비축 방출을 통해 수급안정을 추진한다고 밝혔다.",
            "https://www.korea.kr/briefing/policyBriefingView.do?newsId=148945678",
        )
        syndicated = self._make_article(
            "policy",
            "사과·배 할인 지원 확대… 농식품부 성수품 공급 안정",
            "농식품부는 사과와 배의 할인 지원을 확대하고 성수품 공급과 비축 방출을 통해 수급안정을 추진한다고 밝혔다.",
            "https://www.newsis.com/view/NISX20260310_0004000011",
        )
        deduped = main._dedupe_by_event_key([official, syndicated], "policy")
        self.assertEqual(len(deduped), 1, msg=str([(x.link, x.topic, main._event_key(x, "policy")) for x in deduped]))
        self.assertEqual(deduped[0].link, official.link)


    def test_policy_selection_dedupes_same_official_announcement_story(self):
        official = self._make_article(
            "policy",
            "농식품부, 사과·배 할인 지원 확대… 성수품 수급안정 추진",
            "농식품부는 사과와 배의 할인 지원을 확대하고 성수품 공급과 비축 방출을 통해 수급안정을 추진한다고 밝혔다.",
            "https://www.korea.kr/briefing/policyBriefingView.do?newsId=148945678",
        )
        syndicated = self._make_article(
            "policy",
            "사과·배 할인 지원 확대… 농식품부 성수품 공급 안정",
            "농식품부는 사과와 배의 할인 지원을 확대하고 성수품 공급과 비축 방출을 통해 수급안정을 추진한다고 밝혔다.",
            "https://www.newsis.com/view/NISX20260310_0004000011",
        )
        picked = main.select_top_articles([official, syndicated], "policy", 5)
        picked_urls = {a.link for a in picked}
        self.assertEqual(len(picked_urls & {official.link, syndicated.link}), 1, msg=str([(x.link, x.score, x.topic) for x in picked]))
        self.assertIn(official.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))


    def test_supply_commodity_tokens_include_registry_items(self):
        self.assertIn("딸기", main._SUPPLY_COMMODITY_TOKENS)
        self.assertIn("수박", main._SUPPLY_COMMODITY_TOKENS)


    def test_headline_gate_relaxed_rejects_english_interview_for_supply(self):
        interview = self._make_article(
            "supply",
            "[afl Interview] 안진우 한국 포도 협회 회장",
            "포도 수급 조절위원회 가동과 과잉 물량 대응 계획을 설명했다.",
            "http://www.aflnews.co.kr/news/articleView.html?idxno=315910",
        )
        self.assertFalse(main._headline_gate_relaxed(interview, "supply"))


    def test_supply_feature_refresh_needed_when_full_but_feature_light(self):
        candidates = [
            self._make_article("supply", "저장 배추 물량 감소…시세 상승 기대", "배추 저장 물량이 줄며 도매시장 시세 상승이 예상된다.", "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500277?wlog_tag3=naver"),
            self._make_article("supply", "수박 출하 본격화에도 도매가격 약보합", "수박 출하 물량이 늘었지만 도매시장 가격은 약보합세를 보였다.", "https://www.yna.co.kr/view/AKR20260309000000001"),
            self._make_article("supply", "사과 출하 줄며 가격 상승", "사과 출하량 감소로 도매시장 가격이 오름세를 보였다.", "https://www.fnnews.com/news/202603091111111111"),
            self._make_article("supply", "포도 저장 물량 조정…수급 관리 강화", "포도 저장 물량 조정과 수급 관리가 이뤄지고 있다.", "https://www.nongmin.com/article/20260310500151"),
            self._make_article("supply", "감귤 출하량 감소에 가격 강세", "감귤 출하량 감소로 가격 강세가 이어지고 있다.", "https://www.segye.com/newsView/20260310500001"),
        ]
        candidates[0].score = 25.0
        candidates[1].score = 24.4
        candidates[2].score = 23.9
        candidates[3].score = 23.1
        candidates[4].score = 22.8
        candidates_sorted = sorted(candidates, key=main._sort_key_major_first, reverse=True)
        thr = main._dynamic_threshold(candidates_sorted, "supply")
        self.assertTrue(main._needs_supply_feature_refresh(candidates_sorted, thr, 5))


    def test_supply_seed_coverage_requires_meaningful_item_match_not_incidental_mention(self):
        article = self._make_article(
            "supply",
            "저장 배추 물량 감소…시세 상승 기대",
            "배추 저장 물량이 줄었고 딸기 체험 농가도 봄철 준비에 들어갔다.",
            "https://example.com/cabbage-with-strawberry-mention",
        )
        article.topic = "배추"
        self.assertFalse(main._article_matches_seed_term(article, "딸기"))
        self.assertTrue(main._article_matches_seed_term(article, "배추"))


    def test_supply_recall_fallback_feature_refresh_frontloads_multiple_queries_for_missing_feature_seed(self):
        section_conf = {
            "key": "supply",
            "queries": ["배추 가격", "수박 도매가격", "사과 가격", "포도 가격", "감귤 가격", "딸기 작황", "토마토 작황"],
            "must_terms": ["배추", "수박", "사과", "포도", "감귤", "딸기", "토마토"],
        }
        candidates = [
            self._make_article("supply", "저장 배추 물량 감소…시세 상승 기대", "배추 저장 물량이 줄며 도매시장 시세 상승이 예상된다.", "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500277?wlog_tag3=naver"),
            self._make_article("supply", "수박 출하 본격화에도 도매가격 약보합", "수박 출하 물량이 늘었지만 도매시장 가격은 약보합세를 보였다.", "https://www.yna.co.kr/view/AKR20260309000000001"),
            self._make_article("supply", "사과 출하 줄며 가격 상승", "사과 출하량 감소로 도매시장 가격이 오름세를 보였다.", "https://www.fnnews.com/news/202603091111111111"),
            self._make_article("supply", "포도 저장 물량 조정…수급 관리 강화", "포도 저장 물량 조정과 수급 관리가 이뤄지고 있다.", "https://www.nongmin.com/article/20260310500151"),
            self._make_article("supply", "감귤 출하량 감소에 가격 강세", "감귤 출하량 감소로 가격 강세가 이어지고 있다.", "https://www.segye.com/newsView/20260310500001"),
        ]
        candidates[0].score = 25.0
        candidates[1].score = 24.4
        candidates[2].score = 23.9
        candidates[3].score = 23.1
        candidates[4].score = 22.8
        queries, meta = main._build_recall_fallback_queries("supply", section_conf, candidates, 20.0)
        self.assertGreaterEqual(len(queries), 2, msg=str(meta))
        self.assertEqual(queries[0], "딸기 생육", msg=str(meta))
        self.assertEqual(queries[1], "딸기 난방", msg=str(meta))

    def test_supply_selection_prefers_field_feature_over_generic_tail_item_when_full(self):
        cabbage = self._make_article("supply", "저장 배추 물량 감소…시세 상승 기대", "배추 저장 물량이 줄며 도매시장 시세 상승이 예상된다.", "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500277?wlog_tag3=naver")
        apple = self._make_article("supply", "사과 출하 줄며 가격 상승", "사과 출하량 감소로 도매시장 가격이 오름세를 보였다.", "https://www.fnnews.com/news/202603091111111111")
        grape = self._make_article("supply", "포도 저장 물량 조정…수급 관리 강화", "포도 저장 물량 조정과 수급 관리가 이뤄지고 있다.", "https://www.nongmin.com/article/20260310500151")
        citrus = self._make_article("supply", "감귤 출하량 감소에 가격 강세", "감귤 출하량 감소로 가격 강세가 이어지고 있다.", "https://www.segye.com/newsView/20260310500001")
        watermelon = self._make_article("supply", "수박 출하 본격화에도 도매가격 약보합", "수박 출하 물량이 늘었지만 도매시장 가격은 약보합세를 보였다.", "https://www.yna.co.kr/view/AKR20260309000000001")
        strawberry = self._make_article("supply", "온종일 불때야 하는데 막막 초록색 딸기 바라보며 한숨", "딸기 체험 농장을 운영하는 농가가 생육적온과 난방비 부담을 호소했다.", "https://www.sedaily.com/article/20017059")
        cabbage.score = 30.0
        apple.score = 29.1
        grape.score = 28.2
        citrus.score = 27.4
        watermelon.score = 23.4
        strawberry.score = 22.7
        picked = main.select_top_articles([cabbage, apple, grape, citrus, watermelon, strawberry], "supply", 5)
        picked_urls = {a.link for a in picked}
        self.assertIn(strawberry.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))
        self.assertNotIn(watermelon.link, picked_urls, msg=str([(x.link, x.score, x.topic) for x in picked]))


    def test_supply_selection_keeps_item_feature_story_without_price_signal(self):
        article = self._make_article(
            "supply",
            "“온종일 불때야 하는데 막막” 초록색 딸기 바라보며 한숨",
            "딸기 체험 농장을 운영하는 농가가 생육적온을 맞추기 어려워 난방비 부담이 커졌다고 밝혔다.",
            "https://www.sedaily.com/article/20017059",
        )
        picked = main.select_top_articles([article], "supply", 5)
        self.assertTrue(any(x.link == article.link for x in picked), msg=str([(x.link, x.score) for x in picked]))

    def test_supply_underfill_backfill_keeps_strong_field_story_just_below_threshold(self):
        apple = self._make_article(
            "supply",
            "사과 출하 줄며 가격 상승",
            "사과 출하량 감소로 도매시장 가격이 오름세를 보였다.",
            "https://www.fnnews.com/news/202603091111111111",
        )
        cabbage = self._make_article(
            "supply",
            "저장 배추 물량 감소…시세 상승 기대",
            "배추 저장 물량이 줄며 도매시장 시세 상승이 예상된다.",
            "https://www.seoul.co.kr/news/economy/2026/03/09/20260309500277?wlog_tag3=naver",
        )
        citrus = self._make_article(
            "supply",
            "기름값 지금처럼 오르면 하우스 감귤 못합니다",
            "하우스 감귤 농가가 난방비와 유가 상승으로 생산비 부담이 커졌다고 호소했다.",
            "https://www.sedaily.com/NewsView/2GQ9EXAMPLE",
        )
        apple.score = 30.6
        cabbage.score = 28.9
        citrus.score = 21.4

        picked = main.select_top_articles([apple, cabbage, citrus], "supply", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(citrus.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_supply_underfill_prefers_field_story_over_macro_brief(self):
        apple = self._make_article(
            "supply",
            "사과 출하 줄며 가격 강세",
            "사과 출하량 감소로 도매시장 가격이 오름세를 보이고 있다.",
            "https://www.fnnews.com/news/202603091111111111",
        )
        field = self._make_article(
            "supply",
            "참외 작황·생육 회복 늦어 산지 출하 조절 비상",
            "참외 산지 농가에서 작황 회복이 늦어지고 생육 불균형이 커지면서 출하 조절이 이어지고 있다.",
            "https://www.nongmin.com/article/20260311010101",
        )
        macro = self._make_article(
            "supply",
            "농축산물 가격 전주 대비 하락",
            "농식품부는 사과·배·딸기 등 농축산물 가격이 대체로 전주 대비 하락했다고 밝혔다.",
            "https://www.bokuennews.com/news/article.html?no=260000",
        )
        apple.score = 30.6
        field.score = 28.5
        macro.score = 28.4

        picked = main.select_top_articles([apple, field, macro], "supply", 2)
        picked_links = {x.link for x in picked}
        self.assertIn(field.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertNotIn(macro.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_policy_underfill_backfill_keeps_strong_official_story_just_below_threshold(self):
        major1 = self._make_article(
            "policy",
            "가락·구리 시장 동시휴업…딸기 산지 폐기량 2배 늘고 경락값 '뚝'",
            "도매시장 휴업과 산지 출하 조정으로 딸기 가격이 흔들리자 대응 필요성이 커지고 있다.",
            "https://www.nongmin.com/article/20260310555555",
        )
        major2 = self._make_article(
            "policy",
            "수출·물가 등 경제 '빨간불'…부·울·경 긴급 대응",
            "중동 변수와 유가 상승에 대응해 물가와 수출 상황을 점검하고 민생안정 대책을 추진한다.",
            "https://biz.heraldcorp.com/article/10683302",
        )
        official = self._make_article(
            "policy",
            "농식품부, 과일·채소 수급 점검…가격 안정대책 추진 상황 브리핑",
            "농식품부는 사과·배·딸기 등 과일과 채소 가격 동향을 점검하고 할인지원과 가용물량 투입 계획을 밝혔다.",
            "https://www.korea.kr/news/policyNewsView.do?newsId=148000000",
        )
        major1.score = 31.8
        major2.score = 27.9
        official.score = 22.8

        picked = main.select_top_articles([major1, major2, official], "policy", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(official.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertNotIn(major1.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertNotIn(major2.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_supply_seed_extraction_spreads_across_query_list(self):
        queries = [
            "사과 가격",
            "배 가격",
            "감귤 가격",
            "천혜향 출하",
            "포도 가격",
            "딸기 작황",
            "토마토 작황",
            "화훼 가격",
        ]
        seeds = main._extract_seed_terms_from_queries(queries, limit=6)
        self.assertIn("감귤", seeds)
        self.assertIn("딸기", seeds)
        self.assertIn("화훼", seeds)
        self.assertLessEqual(len(seeds), 6)

    def test_supply_registry_is_single_source_for_item_queries_topics_and_must_terms(self):
        supply_conf = next(sec for sec in main.SECTIONS if sec["key"] == "supply")
        self.assertEqual(supply_conf["queries"], list(main.SUPPLY_ITEM_QUERIES) + list(main.SUPPLY_CONTEXT_QUERIES))
        self.assertEqual(supply_conf["must_terms"], list(main.SUPPLY_GENERAL_MUST_TERMS) + list(main.SUPPLY_ITEM_MUST_TERMS))
        self.assertTrue({entry["topic"] for entry in main.COMMODITY_REGISTRY}.issubset(main._HORTI_TOPICS_SET))
        self.assertIn("무", main._HORTI_TOPICS_SET)
        self.assertIn("양파", main._HORTI_TOPICS_SET)
        self.assertEqual(main.TOPIC_REP_BY_TERM_L["배"], "배")
        self.assertEqual(main.TOPIC_REP_BY_TERM_L["천혜향"], "감귤")
        self.assertEqual(main.TOPIC_REP_BY_TERM_L["월동무"], "무")

    def test_registry_rep_terms_drive_seed_extraction_and_brief_tags(self):
        seeds = main._extract_seed_terms_from_queries(["배 과일 가격", "천혜향 출하", "멜론 도매가격"], limit=6)
        self.assertIn("배", seeds)
        self.assertIn("감귤", seeds)
        self.assertIn("멜론", seeds)

        tags = main._commodity_tags_in_text("천혜향 출하와 신고배 가격, 멜론 작황 점검", limit=5)
        self.assertIn("감귤", tags)
        self.assertIn("배", tags)
        self.assertIn("멜론", tags)

    def test_supply_recall_fallback_queries_include_feature_signals(self):
        section_conf = {
            "key": "supply",
            "queries": ["사과 가격", "배 가격", "감귤 가격", "딸기 작황", "화훼 가격"],
            "must_terms": ["사과", "배", "감귤", "딸기", "화훼"],
        }
        queries, meta = main._build_recall_fallback_queries("supply", section_conf, [], 99.0)
        self.assertIn("감귤 품질", queries, msg=str(meta))
        self.assertIn("딸기 생육", queries, msg=str(meta))

    def test_supply_recall_fallback_queries_prefer_feature_queries_over_raw_or_trade_queries(self):
        section_conf = {
            "key": "supply",
            "queries": ["사과 가격", "배 가격", "감귤 가격", "딸기 작황", "상추 가격", "화훼 가격"],
            "must_terms": ["사과", "배", "감귤", "딸기", "상추", "화훼"],
        }
        queries, meta = main._build_recall_fallback_queries("supply", section_conf, [], 99.0)
        self.assertIn("감귤 품질", queries, msg=str(meta))
        self.assertIn("딸기 생육", queries, msg=str(meta))
        self.assertNotIn("사과", queries, msg=str(meta))
        self.assertNotIn("감귤 무관세", queries, msg=str(meta))
        self.assertNotIn("감귤 수입", queries, msg=str(meta))

    def test_supply_recall_prioritizes_missing_query_seeds_ahead_of_covered_pool_topics(self):
        section_conf = {
            "key": "supply",
            "queries": ["사과 가격", "배 가격", "감귤 가격", "딸기 작황", "상추 가격", "화훼 가격"],
            "must_terms": ["사과", "배", "감귤", "딸기", "상추", "화훼"],
        }
        covered = self._make_article(
            "supply",
            "제주 감귤 출하 동향",
            "제주 감귤 작황과 출하 흐름을 점검했다.",
            "https://example.com/citrus-covered",
        )
        covered.topic = "감귤/만감"
        covered.score = 12.0

        queries, meta = main._build_recall_fallback_queries("supply", section_conf, [covered], 7.0)
        self.assertIn("딸기 생육", queries, msg=str(meta))
        self.assertNotIn("감귤 품질", queries, msg=str(meta))

    def test_supply_seed_coverage_ignores_body_only_mentions(self):
        article = self._make_article(
            "supply",
            "농식품부 과일 수급 점검 결과",
            "과일류 가격 흐름을 설명하며 딸기와 감귤 가격도 전년 대비로 언급했다.",
            "https://example.com/policy-brief-body-only",
        )
        article.topic = "정책"
        self.assertFalse(main._article_matches_seed_term(article, "딸기"))
        self.assertFalse(main._article_matches_seed_term(article, "감귤"))

    def test_supply_underfilled_refresh_diversifies_focus_profiles(self):
        section_conf = {
            "key": "supply",
            "queries": ["감귤 가격", "딸기 작황", "토마토 가격"],
            "must_terms": ["감귤", "딸기", "토마토"],
        }
        cabbage = self._make_article(
            "supply",
            "가락시장 배추 반입 늘어 도매가 안정",
            "배추 반입량과 도매가격 흐름을 전했다.",
            "https://example.com/cabbage-core",
        )
        cabbage.topic = "배추"
        cabbage.score = 14.0
        flower = self._make_article(
            "supply",
            "화훼 농가 난방비 부담 커져",
            "절화 농가가 난방비와 유가 부담을 호소했다.",
            "https://example.com/flower-feature",
        )
        flower.topic = "화훼"
        flower.score = 12.0
        interview = self._make_article(
            "supply",
            "[afl Interview] 안진우 한국 포도 협회 회장",
            "포도 산업과 자조금 계획을 인터뷰 형식으로 소개했다.",
            "https://example.com/grape-interview",
        )
        interview.topic = "포도"
        interview.score = 10.2

        queries, meta = main._build_recall_fallback_queries("supply", section_conf, [cabbage, flower, interview], 7.0)
        self.assertIn("딸기 생육", queries, msg=str(meta))
        self.assertIn("감귤 품질", queries, msg=str(meta))
        self.assertIn("농산물 가격 동향", queries, msg=str(meta))
    def test_collect_candidates_uses_supply_feature_recall_query_when_pool_is_thin(self):
        section_conf = {
            "key": "supply",
            "queries": ["사과 가격", "배 가격", "감귤 가격", "딸기 작황"],
            "must_terms": ["사과", "배", "감귤", "딸기", "화훼"],
        }
        start_kst = main.dt_kst(main.date(2026, 3, 9), main.REPORT_HOUR_KST)
        end_kst = main.dt_kst(main.date(2026, 3, 10), main.REPORT_HOUR_KST)
        seen_queries = []
        old_func = main.naver_news_search_paged
        try:
            def _fake_search(q, display=50, pages=1, sort="date"):
                seen_queries.append(q)
                if q == "딸기 생육":
                    return {
                        "items": [
                            {
                                "title": "온종일 불때야 하는데 막막 초록색 딸기 바라보며 한숨",
                                "description": "딸기 체험 농장을 운영하는 농가가 생육적온과 난방비 부담을 호소했다.",
                                "link": "https://www.sedaily.com/article/20017059",
                                "originallink": "https://www.sedaily.com/article/20017059",
                                "pubDate": "Mon, 09 Mar 2026 08:45:35 +0000",
                            }
                        ]
                    }
                return {"items": []}

            main.naver_news_search_paged = _fake_search
            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_func

        self.assertIn("딸기 생육", seen_queries, msg=str(seen_queries))
        self.assertTrue(any("20017059" in (a.link or "") for a in items), msg=str([(a.link, a.title) for a in items]))

    def test_collect_candidates_can_recall_policy_market_brief_story(self):
        section_conf = next(sec for sec in main.SECTIONS if sec["key"] == "policy")
        start_kst = main.dt_kst(main.date(2026, 3, 9), main.REPORT_HOUR_KST)
        end_kst = main.dt_kst(main.date(2026, 3, 10), main.REPORT_HOUR_KST)
        seen_queries = []
        old_func = main.naver_news_search_paged
        try:
            def _fake_search(q, display=50, pages=1, sort="date"):
                seen_queries.append(q)
                if q == "농산물 가격 동향":
                    return {
                        "items": [
                            {
                                "title": "농축산물 가격 대체로 하락세…중동 전쟁에 따른 농산물 수급 영향 '제한적'",
                                "description": "최근 중동 전쟁 여파에도 농산물 수급 영향은 제한적이라는 점검 결과와 함께 과일류 가격 흐름을 설명했다.",
                                "link": "https://www.nocutnews.co.kr/news/6481885",
                                "originallink": "https://www.nocutnews.co.kr/news/6481885",
                                "pubDate": "Mon, 09 Mar 2026 09:35:00 +0000",
                            }
                        ]
                    }
                return {"items": []}

            main.naver_news_search_paged = _fake_search
            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_func

        self.assertIn("농산물 가격 동향", seen_queries, msg=str(seen_queries))
        self.assertTrue(any("6481885" in (a.link or "") for a in items), msg=str([(a.link, a.title) for a in items]))



    def test_collect_candidates_can_recall_policy_market_brief_story_via_check_query(self):
        section_conf = next(sec for sec in main.SECTIONS if sec["key"] == "policy")
        start_kst = main.dt_kst(main.date(2026, 3, 9), main.REPORT_HOUR_KST)
        end_kst = main.dt_kst(main.date(2026, 3, 10), main.REPORT_HOUR_KST)
        seen_queries = []
        old_func = main.naver_news_search_paged
        try:
            def _fake_search(q, display=50, pages=1, sort="date"):
                seen_queries.append(q)
                if q == "농식품부 수급 점검":
                    return {
                        "items": [
                            {
                                "title": "농축산물 가격 대체로 하락세지만 과일값은 제한적",
                                "description": "농식품부가 수급 점검 결과를 설명하며 정부 가용물량과 과일류 가격 흐름을 짚었다.",
                                "link": "https://www.nocutnews.co.kr/news/6481885",
                                "originallink": "https://www.nocutnews.co.kr/news/6481885",
                                "pubDate": "Mon, 09 Mar 2026 09:35:00 +0000",
                            }
                        ]
                    }
                return {"items": []}

            main.naver_news_search_paged = _fake_search
            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_func

        self.assertIn("농식품부 수급 점검", seen_queries, msg=str(seen_queries))
        self.assertTrue(any("6481885" in (a.link or "") for a in items), msg=str([(a.link, a.title) for a in items]))
    def test_supply_fallback_recall_runs_even_when_cond_paging_is_disabled(self):
        section_conf = {
            "key": "supply",
            "queries": ["사과 가격", "배 가격", "감귤 가격", "딸기 작황"],
            "must_terms": ["사과", "배", "감귤", "딸기", "화훼"],
        }
        start_kst = main.dt_kst(main.date(2026, 3, 9), main.REPORT_HOUR_KST)
        end_kst = main.dt_kst(main.date(2026, 3, 10), main.REPORT_HOUR_KST)
        seen_queries = []
        old_func = main.naver_news_search_paged
        old_cond = main.COND_PAGING_ENABLED
        old_fb_cap = main.COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION
        old_budget_used = main._COND_PAGING_EXTRA_CALLS_USED
        try:
            main.COND_PAGING_ENABLED = False
            main.COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION = 2
            main._COND_PAGING_EXTRA_CALLS_USED = 0

            def _fake_search(q, display=50, pages=1, sort="date"):
                seen_queries.append(q)
                if q == "딸기 생육":
                    return {
                        "items": [
                            {
                                "title": "온종일 불때야 하는데 막막 초록색 딸기 바라보며 한숨",
                                "description": "딸기 체험 농장을 운영하는 농가가 생육적온과 난방비 부담을 호소했다.",
                                "link": "https://www.sedaily.com/article/20017059",
                                "originallink": "https://www.sedaily.com/article/20017059",
                                "pubDate": "Mon, 09 Mar 2026 08:45:35 +0000",
                            }
                        ]
                    }
                return {"items": []}

            main.naver_news_search_paged = _fake_search
            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_func
            main.COND_PAGING_ENABLED = old_cond
            main.COND_PAGING_FALLBACK_QUERY_CAP_PER_SECTION = old_fb_cap
            main._COND_PAGING_EXTRA_CALLS_USED = old_budget_used

        self.assertIn("딸기 생육", seen_queries, msg=str(seen_queries))
        self.assertTrue(any("20017059" in (a.link or "") for a in items), msg=str([(a.link, a.title) for a in items]))

    def test_supply_fallback_recall_keeps_reserved_budget_after_other_section_consumption(self):
        section_conf = {
            "key": "supply",
            "queries": ["사과 가격", "배 가격", "감귤 가격", "딸기 작황"],
            "must_terms": ["사과", "배", "감귤", "딸기", "화훼"],
        }
        start_kst = main.dt_kst(main.date(2026, 3, 9), main.REPORT_HOUR_KST)
        end_kst = main.dt_kst(main.date(2026, 3, 10), main.REPORT_HOUR_KST)
        seen_queries = []
        old_func = main.naver_news_search_paged
        old_budget_total = main.COND_PAGING_EXTRA_CALL_BUDGET_TOTAL
        old_reserved = main.COND_PAGING_RESERVED_CALLS_PER_SECTION
        old_budget_used = main._COND_PAGING_EXTRA_CALLS_USED
        old_budget_by_section = dict(main._COND_PAGING_EXTRA_CALLS_BY_SECTION)
        try:
            main.COND_PAGING_EXTRA_CALL_BUDGET_TOTAL = 12
            main.COND_PAGING_RESERVED_CALLS_PER_SECTION = 2
            main._COND_PAGING_EXTRA_CALLS_USED = 10
            main._COND_PAGING_EXTRA_CALLS_BY_SECTION = {"policy": 10}

            def _fake_search(q, display=50, pages=1, sort="date"):
                seen_queries.append(q)
                if q == "딸기 생육":
                    return {
                        "items": [
                            {
                                "title": "온종일 불때야 하는데 막막 초록색 딸기 바라보며 한숨",
                                "description": "딸기 체험 농장을 운영하는 농가가 생육적온과 난방비 부담을 호소했다.",
                                "link": "https://www.sedaily.com/article/20017059",
                                "originallink": "https://www.sedaily.com/article/20017059",
                                "pubDate": "Mon, 09 Mar 2026 08:45:35 +0000",
                            }
                        ]
                    }
                return {"items": []}

            main.naver_news_search_paged = _fake_search
            items = main.collect_candidates_for_section(section_conf, start_kst, end_kst)
        finally:
            main.naver_news_search_paged = old_func
            main.COND_PAGING_EXTRA_CALL_BUDGET_TOTAL = old_budget_total
            main.COND_PAGING_RESERVED_CALLS_PER_SECTION = old_reserved
            main._COND_PAGING_EXTRA_CALLS_USED = old_budget_used
            main._COND_PAGING_EXTRA_CALLS_BY_SECTION = old_budget_by_section

        self.assertIn("딸기 생육", seen_queries, msg=str(seen_queries))
        self.assertTrue(any("20017059" in (a.link or "") for a in items), msg=str([(a.link, a.title) for a in items]))

    def test_trade_terms_do_not_map_to_item_topics(self):
        self.assertNotIn("무관세", main.HORTI_ITEM_TERMS_L)
        self.assertNotIn("fta", main.HORTI_ITEM_TERMS_L)
        self.assertNotIn("무관세", main.TOPIC_REP_BY_TERM_L)

    def test_supply_feature_context_generalizes_to_yuja_and_kiwi(self):
        field_kind = main.supply_feature_context_kind(
            "유자 작황 부진에 산지 농가 긴장",
            "꽃샘추위로 유자 착과가 늦어지고 농가가 생육 관리 부담을 호소했다.",
        )
        quality_kind = main.supply_feature_context_kind(
            "국산 키위, 수입산보다 당도·선호도 앞서",
            "참다래 블라인드 비교에서 국내산 키위가 품질 경쟁력과 소비자 선호도를 보였다.",
        )
        self.assertEqual(field_kind, "field")
        self.assertEqual(quality_kind, "quality")

    def test_supply_recall_fallback_queries_stay_balanced_for_non_target_items(self):
        section_conf = {
            "key": "supply",
            "queries": ["유자 가격", "키위 가격", "상추 가격", "자두 가격", "매실 가격"],
            "must_terms": ["유자", "키위", "상추", "자두", "매실"],
        }
        queries, meta = main._build_recall_fallback_queries("supply", section_conf, [], 99.0)
        self.assertIn("유자 작황", queries, msg=str(meta))
        self.assertIn("키위 작황", queries, msg=str(meta))
        self.assertIn("상추 작황", queries, msg=str(meta))
        self.assertNotIn("딸기 생육", queries, msg=str(meta))
        self.assertNotIn("감귤 품질", queries, msg=str(meta))

    def test_extract_topic_recognizes_lettuce(self):
        topic = main.extract_topic(
            "상추 작황 부진에 산지 출하량 감소",
            "상추 농가가 한파 뒤 생육 회복 속도가 늦어져 출하량 감소를 우려했다.",
        )
        self.assertEqual(topic, "상추")

    def test_extract_topic_does_not_treat_processed_potato_lifestyle_story_as_potato(self):
        topic = main.extract_topic(
            "주말 감튀 어떻냐…서울 미식가들 줄 세운 새 메뉴",
            "감자튀김과 버거 조합을 소개하는 외식 트렌드 기사다.",
        )
        self.assertNotEqual(topic, "감자")
        self.assertFalse(main.is_fresh_potato_context("주말 감튀 어떻냐…감자튀김과 버거 조합"))

    def test_dist_export_field_requires_horti_anchor_for_k_food_brief(self):
        title = "KGC인삼공사 부여공장서 K-푸드 현장 간담회"
        desc = "농식품부와 업계가 홍삼 수출 비관세장벽 대응 방안을 논의했다."
        self.assertFalse(main.is_dist_export_field_context(title, desc, "biz.heraldcorp.com", "헤럴드경제"))

    def test_policy_export_support_brief_requires_horti_anchor(self):
        title = "농식품부, KGC인삼공사와 홍삼 수출 규제 해소 방안 논의"
        desc = "K-푸드 수출 확대를 위해 비관세 장벽 대응과 간담회를 진행했다."
        self.assertFalse(main.is_policy_export_support_brief_context(title, desc, "mk.co.kr", "매일경제"))

    def test_low_tier_policy_source_does_not_take_core_over_major_sources(self):
        low = self._make_article(
            "policy",
            "농축산물 물가 1%대 안정, 수급 안정책·할인지원에 예산 집중 투입",
            "농식품부는 농축산물 가격 안정을 위해 정부 예산을 집중 투입하고 사과 수급 안정 대책을 이어간다.",
            "https://www.farmnmarket.com/news/article.html?no=25786",
        )
        major1 = self._make_article(
            "policy",
            "농산물 최대 50% 할인 지원…정부 '생산유통거리 가격 안정 총력'",
            "농림축산식품부가 농산물 가격 안정을 위해 할인 지원과 공급 안정 조치를 이어간다.",
            "https://www.nongmin.com/article/20260306500258",
        )
        major2 = self._make_article(
            "policy",
            "정부 '물가, 중동 사태 따른 국제 유가 변수'",
            "농축수산물 물가 안정세를 보이고 있으나 유가와 물가 불확실성이 다시 커지고 있다.",
            "https://it.chosun.com/news/articleView.html?idxno=2023092158205",
        )

        picked = main.select_top_articles([low, major1, major2], "policy", 5)
        low_picked = next((x for x in picked if x.link == low.link), None)
        self.assertTrue(low_picked is None or (not getattr(low_picked, "is_core", False)), msg=str([(x.link, x.score, x.is_core) for x in picked]))
        self.assertTrue(any(getattr(x, "is_core", False) for x in picked if x.link in {major1.link, major2.link}), msg=str([(x.link, x.score, x.is_core) for x in picked]))

    def test_policy_selection_keeps_market_brief_alongside_official_policy_story(self):
        market_brief = self._make_article(
            "policy",
            "농축산물 가격 대체로 하락세…중동 전쟁에 따른 농산물 수급 영향 '제한적'",
            "최근 중동 전쟁 여파에도 농산물 수급 영향은 제한적이라는 점검 결과와 함께 과일류 가격 흐름을 설명했다.",
            "https://www.nocutnews.co.kr/news/6481885",
        )
        official = self._make_article(
            "policy",
            "농식품부 '축산물 가격 전년보다 비슷…달걀·과일 일부 수급 불안 관리'",
            "농식품부가 주요 농축산물 수급과 가격 점검 결과를 설명하고 추가 대응 방안을 발표했다.",
            "https://www.yna.co.kr/view/AKR20260309156300030?input=1195m",
        )
        market_brief.score = 29.2
        official.score = 30.4
        picked = main.select_top_articles([market_brief, official], "policy", 5)
        picked_urls = {a.link for a in picked}
        self.assertIn(market_brief.link, picked_urls, msg=str([(x.link, x.score, x.is_core) for x in picked]))
        self.assertIn(official.link, picked_urls, msg=str([(x.link, x.score, x.is_core) for x in picked]))

    def test_local_coop_feature_does_not_fill_dist_tail(self):
        local = self._make_article(
            "dist",
            "경주 현곡농협, 수출 등 활발한 경제사업으로 농가실익 증진",
            "경주 현곡농협이 샤인머스캣 농가의 수출을 통해 경제적 실익을 증진하고 있다. 대만 수출과 GAP 인증 농가 참여가 이어지고 있다.",
            "https://www.nongmin.com/article/20260306500345",
        )
        strong1 = self._make_article(
            "dist",
            "농산물 유통의 진화…새벽 경매에서 온라인 거래로",
            "농산물 유통이 온라인 거래로 변화하며 경매와 물류 효율화가 빨라지고 있다.",
            "https://www.newspim.com/news/view/20260305001313",
        )
        strong2 = self._make_article(
            "dist",
            "흥양농협, 원예농산물 산지유통센터 준공 식 개최",
            "원예농산물 산지유통센터 준공으로 선별과 유통 효율성이 높아질 전망이다.",
            "http://www.aflnews.co.kr/news/articleView.html?idxno=315801",
        )

        picked = main.select_top_articles([strong1, strong2, local], "dist", 5)
        picked_urls = {x.link for x in picked}
        self.assertNotIn(local.link, picked_urls, msg=str([(x.link, x.score, x.is_core) for x in picked]))

    def test_global_reassign_moves_export_shipping_story_from_supply_to_dist(self):
        title = "‘굿뜨래 싱싱 딸기 ’ 몽골행…1t 선적"
        desc = "부여 서부여농협은 국내 딸기 가격 변동에 대응하기 위해 1t의 ‘굿뜨래 싱싱 딸기’를 몽골로 수출했다. 이는 농가 소득 증대에 도움을 주려는 노력의 일환이다."
        url = "https://www.nongmin.com/article/20260309500740"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        a = main.Article(
            section="supply",
            title=title,
            description=desc,
            link=url,
            originallink=url,
            pub_dt_kst=self.now,
            domain=dom,
            press=press,
            canon_url=main.canonicalize_url(url),
            title_key=main.norm_title_key(title),
            norm_key=main.make_norm_key(main.canonicalize_url(url), press, main.norm_title_key(title)),
            topic=main.extract_topic(title, desc),
            score=main.compute_rank_score(title, desc, dom, self.now, self.conf["supply"], press),
        )
        by = {"policy": [], "supply": [a], "dist": [], "pest": []}
        moved = main._global_section_reassign(by, self.now, self.now)
        self.assertGreaterEqual(moved, 1)
        self.assertEqual(len(by["dist"]), 1)
        self.assertEqual(by["dist"][0].section, "dist")

    def test_dev_render_and_kakao_message_are_labeled(self):
        orig = main.DEV_SINGLE_PAGE_MODE
        main.DEV_SINGLE_PAGE_MODE = True
        try:
            empty = {"supply": [], "policy": [], "dist": [], "pest": []}
            html = main.render_daily_page(
                "2026-03-09",
                self.now,
                self.now + timedelta(hours=72),
                empty,
                ["2026-03-09"],
                "/agri-news-brief/dev/",
            )
            msg = main.build_kakao_message("2026-03-09", empty)
        finally:
            main.DEV_SINGLE_PAGE_MODE = orig

        self.assertIn("DEV", html)
        self.assertIn("개발 버전 미리보기", html)
        self.assertIn('/agri-news-brief/dev/index.html', html)
        self.assertNotIn('/agri-news-brief/dev/archive/2026-03-09.html', html)
        self.assertIn("agri-rendered-at-kst", html)
        self.assertIn("agri-dev-version-url", html)
        self.assertIn("version.json", html)
        self.assertIn("syncLatestDevBuild", html)
        self.assertIn("DEV build", html)
        self.assertTrue(msg.splitlines()[0].startswith("[DEV] "), msg=msg)
        self.assertIn("개발 테스트 버전(운영 아님)", msg)


    def test_dist_market_disruption_story_prefers_dist_over_supply(self):
        title = "수도권 도매시장 첫 동시 휴업···출하쏠림에 과채류 가격 '휘청'"
        desc = "수도권 도매시장 동시 휴업으로 출하가 몰리며 과채류 가격이 흔들리고 산지 출하 농민 불안이 커졌다는 현장 기사다."
        best, scores = self._best_section(title, desc, "https://www.agrinet.co.kr/news/articleView.html?idxno=402440")
        self.assertEqual(best, "dist", msg=f"scores={scores}")

    def test_dist_systemic_market_disruption_can_take_core_slot(self):
        export_story = self._make_article(
            "dist",
            "‘굿뜨래 싱싱딸기’ 몽골행…1t 선적",
            "충남 부여군의 딸기 수출 선적 소식으로 산지유통과 수출 현장 흐름을 보여주는 기사다.",
            "https://www.nongmin.com/article/20260309500740",
        )
        followup_story = self._make_article(
            "dist",
            "가락·구리 시장 동시휴업…딸기 산지 폐기량 2배 늘고 경락값 ‘뚝’",
            "가락시장과 구리시장이 동시에 휴업하면서 딸기 가격과 출하량이 크게 흔들렸다는 현장 기사다.",
            "https://www.nongmin.com/article/20260309500761",
        )
        systemic_story = self._make_article(
            "dist",
            "수도권 도매시장 첫 동시 휴업···출하쏠림에 과채류 가격 '휘청'",
            "수도권 도매시장 동시 휴업으로 출하가 몰리며 과채류 가격이 흔들리고 산지 출하 농민 불안이 커졌다는 현장 기사다.",
            "https://www.agrinet.co.kr/news/articleView.html?idxno=402440",
        )
        picked = main.select_top_articles([export_story, followup_story, systemic_story], "dist", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(systemic_story.link, picked_links, msg=str([(x.link, x.score, x.is_core) for x in picked]))
        self.assertTrue(any(x.link == systemic_story.link and getattr(x, "is_core", False) for x in picked), msg=str([(x.link, x.score, x.is_core) for x in picked]))

    def test_supply_issue_bucket_detects_export_recovery_story(self):
        title = "[신선농산물 수출확대 극복 과제] 샤인머스캣 수출 급증했지만, 떨어진 가격 회복 시급"
        desc = "샤인머스캣 수출은 늘었지만 산지 가격 회복과 판로 정상화 대책이 시급하다는 분석이다."
        bucket = main.supply_issue_context_bucket(title, desc)
        best, scores = self._best_section(title, desc, "https://www.agrinet.co.kr/news/articleView.html?idxno=402455")
        self.assertEqual(bucket, "export_recovery")
        self.assertEqual(best, "supply", msg=f"scores={scores}")

    def test_supply_issue_bucket_detects_truncated_export_recovery_story(self):
        title = "[\uC2E0\uC120\uB18D\uC0B0\uBB3C \uC218\uCD9C\uD655\uB300 \uADF9\uBCF5 \uACFC\uC81C] \uC0E4\uC778\uBA38\uC2A4\uCF13 \uC218\uCD9C \uAE09\uC99D\uD588\uC9C0\uB9CC, \uB5A8\uC5B4\uC9C4..."
        desc = "\uB300\uB9CC \uC218\uCD9C \uAE09\uC99D \uB0AE\uC740 \uAC00\uACA9 \uC6B0\uB824"
        bucket = main.supply_issue_context_bucket(title, desc)
        best, scores = self._best_section(title, desc, "https://www.agrinet.co.kr/news/articleView.html?idxno=402455")
        self.assertEqual(bucket, "export_recovery")
        self.assertEqual(best, "supply", msg=f"scores={scores}")

    def test_supply_issue_bucket_detects_commodity_issue_editorial(self):
        title = "[\uCDE8\uC7AC\uC218\uCCA9] \uC0E4\uC778\uBA38\uC2A4\uCEA3 \uC2E4\uC9C8\uC801\uC778 \uB300\uCC45 \uC11C\uB458\uB7EC\uB77C"
        desc = "\uC0E4\uC778\uBA38\uC2A4\uCEA3 \uC0DD\uC0B0\uACFC\uC789 \uBBF8\uC219\uACFC \uC81C\uAC12 \uD3D0\uC6D0 \uC9C0\uC6D0 \uC885\uD569\uACC4\uD68D \uC2DC\uAE09"
        bucket = main.supply_issue_context_bucket(title, desc)
        best, scores = self._best_section(title, desc, "https://www.nongmin.com/article/20260309500634")
        self.assertEqual(bucket, "commodity_issue")
        self.assertEqual(best, "supply", msg=f"scores={scores}")

    def test_supply_issue_articles_with_different_buckets_can_coexist(self):
        export_story = self._make_article(
            "supply",
            "\uC0E4\uC778\uBA38\uC2A4\uCEA3 \uC218\uCD9C \uD655\uB300 \uD68C\uBCF5 \uB300\uCC45 \uC2DC\uAE09",
            "\uC0E4\uC778\uBA38\uC2A4\uCEA3 \uC218\uCD9C \uAE09\uC99D \uAC00\uACA9 \uD558\uB77D \uD310\uB85C \uD68C\uBCF5 \uB300\uCC45",
            "https://www.agrinet.co.kr/news/articleView.html?idxno=402455",
        )
        farm_story = self._make_article(
            "supply",
            "[\uCDE8\uC7AC\uC218\uCCA9] \uC0E4\uC778\uBA38\uC2A4\uCEA3 \uC2E4\uC9C8\uC801\uC778 \uB300\uCC45 \uC11C\uB458\uB7EC\uB77C",
            "\uC0E4\uC778\uBA38\uC2A4\uCEA3 \uC0DD\uC0B0\uACFC\uC789 \uBBF8\uC219\uACFC \uC81C\uAC12 \uD3D0\uC6D0 \uC9C0\uC6D0 \uC885\uD569\uACC4\uD68D \uC2DC\uAE09",
            "https://www.nongmin.com/article/20260309500634",
        )
        export_story.score = 24.8
        farm_story.score = 23.7
        picked = main.select_top_articles([export_story, farm_story], "supply", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(export_story.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertIn(farm_story.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_pest_distinct_regional_execution_stories_can_coexist_when_strong(self):
        generic = self._make_article(
            "pest",
            "과수화상병 확산 막는다…전국 예찰 강화",
            "과수화상병 확산 차단을 위해 전국 예찰과 방제 체계를 강화한다.",
            "https://www.newsis.com/view/NISX20260311_0001111111",
        )
        region1 = self._make_article(
            "pest",
            "영월군, 과수화상병 예방 방제 약제 공급",
            "영월군이 과수화상병 예방을 위해 약제를 공급하고 과원 예찰을 강화한다.",
            "http://www.youngnong.co.kr/news/articleView.html?idxno=57999",
        )
        region2 = self._make_article(
            "pest",
            "충주시, 과수화상병 전수조사·예찰 총력",
            "충주시가 과수화상병 차단을 위해 전수조사와 현장 예찰을 강화한다.",
            "https://www.nongmin.com/article/20260311555555",
        )
        region3 = self._make_article(
            "pest",
            "진주시, 과수화상병 방제 약제 무상 공급",
            "진주시가 과수화상병 방제 약제를 무상 공급하고 농가 현장 대응에 나선다.",
            "https://www.news1.kr/local/test/9999999",
        )
        generic.score = 20.0
        region1.score = 19.5
        region2.score = 19.4
        region3.score = 19.3

        self.assertFalse(main._is_similar_story(region1, region2, "pest"))
        self.assertFalse(main._is_similar_story(region2, region3, "pest"))

        picked = main.select_top_articles([generic, region1, region2, region3], "pest", 4)
        picked_links = {x.link for x in picked}
        self.assertEqual(len(picked), 4, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertIn(region1.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertIn(region2.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertIn(region3.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_remote_foreign_trade_brief_is_filtered_from_policy_and_dist(self):
        title = "미국·인도네시아 상호무역협정(ART) 서명"
        desc = "미국과 인도네시아가 상호무역협정을 체결했다는 KOTRA 브리프로 국내 농산물·원예 수급이나 유통 현장과 직접 연결되는 설명은 없다."
        url = "https://dream.kotra.or.kr/kotranews/cms/news/actionKotraBoardDetail.do?SITE_NO=3&MENU_ID=90&CONTENTS_NO=1&bbsGbn=244&bbsSn=244&pNttSn=239392"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        self.assertFalse(main.is_relevant(title, desc, dom, url, self.conf["policy"], press))
        self.assertFalse(main.is_relevant(title, desc, dom, url, self.conf["dist"], press))

    def test_policy_export_support_brief_prefers_policy_but_stays_noncore(self):
        title = "송미령 농식품부 장관 'K-푸드 수출 160억불…유통 개혁·AI 접목으로 식품산업 혁신'"
        desc = "농식품부 장관이 K-푸드 수출 확대 목표와 유통 개혁, AI 접목, 식품산업 혁신 방안을 설명했다."
        url = "https://cooknchefnews.com/news/view/1065603268596477"
        best, scores = self._best_section(title, desc, url)
        self.assertEqual(best, "policy", msg=f"scores={scores}")

        brief = self._make_article("policy", title, desc, url)
        strong1 = self._make_article(
            "policy",
            "농식품부, 사과·배 수급안정 대책 발표",
            "농식품부가 과일 수급 안정과 가격 대응 방안을 발표했다.",
            "https://www.yna.co.kr/view/AKR20260311000100030",
        )
        strong2 = self._make_article(
            "policy",
            "정부, 온라인 도매시장 확대와 원산지 단속 강화 추진",
            "정부가 온라인 도매시장 확대와 원산지 단속 강화 계획을 내놨다.",
            "https://www.newsis.com/view/NISX20260311_0001112222",
        )
        brief.score = max(brief.score, 23.6)
        strong1.score = max(strong1.score, 29.8)
        strong2.score = max(strong2.score, 28.9)

        picked = main.select_top_articles([brief, strong1, strong2], "policy", 5)
        brief_picked = next((x for x in picked if x.link == brief.link), None)
        self.assertIsNotNone(brief_picked, msg=str([(x.link, x.score, x.is_core) for x in picked]))
        self.assertFalse(getattr(brief_picked, "is_core", False), msg=str([(x.link, x.score, x.is_core) for x in picked]))

    def test_dist_export_field_story_prefers_dist_over_policy(self):
        title = "'K푸드를 제2 반도체로…짝퉁 근절하고 수출시장 다변화'"
        desc = "홍문표 aT 사장이 인터뷰에서 K푸드 수출시장 다변화, 유통 구조 개선, 온라인 도매시장, 직거래 플랫폼 등 현장 과제를 설명했다."
        best, scores = self._best_section(title, desc, "https://www.donga.com/news/Economy/article/all/20260311/133511391/2")
        self.assertEqual(best, "dist", msg=f"scores={scores}")

    def test_global_reassign_moves_dist_export_field_story_from_policy_to_dist(self):
        title = "'K푸드를 제2 반도체로…짝퉁 근절하고 수출시장 다변화'"
        desc = "홍문표 aT 사장이 인터뷰에서 K푸드 수출시장 다변화, 유통 구조 개선, 온라인 도매시장, 직거래 플랫폼 등 현장 과제를 설명했다."
        url = "https://www.donga.com/news/Economy/article/all/20260311/133511391/2"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        a = main.Article(
            section="policy",
            title=title,
            description=desc,
            link=url,
            originallink=url,
            pub_dt_kst=self.now,
            domain=dom,
            press=press,
            canon_url=main.canonicalize_url(url),
            title_key=main.norm_title_key(title),
            norm_key=main.make_norm_key(main.canonicalize_url(url), press, main.norm_title_key(title)),
            topic=main.extract_topic(title, desc),
            score=18.0,
        )
        by = {"policy": [a], "supply": [], "dist": [], "pest": []}
        moved = main._global_section_reassign(by, self.now, self.now)
        self.assertGreaterEqual(moved, 1)
        self.assertEqual(len(by["dist"]), 1)
        self.assertEqual(by["dist"][0].section, "dist")

    def test_supply_shock_issue_story_prefers_supply(self):
        title = "\ub300\ud615 \uc0b0\ubd88\uc5d0 \uae30\ud6c4\ubcc0\ud654\uae4c\uc9c0\u2026\uacfc\uc218 \ubb18\ubaa9 \ud488\uadc0\uc5d0 \ub18d\uac00 \uc6b8\uc0c1"
        desc = "\uc0b0\ubd88\uacfc \uae30\ud6c4\ubcc0\ud654 \uc5ec\ud30c\ub85c \uacfc\uc218 \ubb18\ubaa9 \ud488\uadc0\uac00 \uc774\uc5b4\uc9c0\uba70 \ub18d\uac00 \ubd80\ub2f4\uc774 \ucee4\uc84c\ub2e4\ub294 \ud604\uc7a5 \uae30\uc0ac\ub2e4."
        bucket = main.supply_issue_context_bucket(title, desc)
        best, scores = self._best_section(title, desc, "https://news.kbs.co.kr/news/pc/view/view.do?ncd=8506106")
        self.assertEqual(bucket, "commodity_issue")
        self.assertEqual(best, "supply", msg=f"scores={scores}")

    def test_dist_local_field_profile_story_prefers_dist_and_is_not_tail(self):
        title = "\uc9c0\uc5ed\uacbd\uc81c \uc120\ub3c4\ud558\ub294 \ud488\ubaa9\ub18d\ud611 - \ub300\uacbd \uc0ac\uacfc \uc6d0\uc608\ub18d\ud611"
        desc = "\ub300\uacbd \uc0ac\uacfc \uc6d0\uc608\ub18d\ud611\uc774 \uacf5\ub3d9\uc120\ubcc4\uacfc \uc0b0\uc9c0\uc720\ud1b5, \ud310\ub85c \ud655\ub300 \ub4f1 \uacbd\uc81c\uc0ac\uc5c5\uc73c\ub85c \uc9c0\uc5ed\uacbd\uc81c\ub97c \uc120\ub3c4\ud55c\ub2e4\ub294 \ud604\uc7a5 \uae30\uc0ac\ub2e4."
        url = "http://www.wonyesanup.co.kr/news/articleView.html?idxno=64002"
        best, scores = self._best_section(title, desc, url)
        self.assertTrue(main.is_dist_local_field_profile_context(title, desc))
        self.assertFalse(main.is_dist_local_org_tail_context(title, desc))
        self.assertEqual(best, "dist", msg=f"scores={scores}")

    def test_dist_online_market_reform_story_prefers_dist(self):
        title = "\uc628\ub77c\uc778\ub3c4\ub9e4\uc2dc\uc7a5 \uc81c\ub3c4 \uac1c\uc120 \ub098\uc130\ub2e4"
        desc = "\uc628\ub77c\uc778 \ub3c4\ub9e4\uc2dc\uc7a5 \uc81c\ub3c4 \uac1c\uc120\uacfc \uac70\ub798 \uaddc\uce59 \ubcf4\uc644\uc73c\ub85c \uc0b0\uc9c0\uc720\ud1b5\uacfc \ub3c4\ub9e4\uc2dc\uc7a5 \ud604\uc7a5 \ud6a8\uc728\uc744 \ub192\uc774\ub824\ub294 \uae30\uc0ac\ub2e4."
        best, scores = self._best_section(title, desc, "https://www.agrinet.co.kr/news/articleView.html?idxno=402439")
        self.assertEqual(best, "dist", msg=f"scores={scores}")

    def test_normalize_press_label_uses_korean_host_name_for_ascii_label(self):
        self.assertEqual(
            main.normalize_press_label("wonyesanup", "http://www.wonyesanup.co.kr/news/articleView.html?idxno=64002"),
            "\uc6d0\uc608\uc0b0\uc5c5\uc2e0\ubb38",
        )
        self.assertEqual(
            main.normalize_press_label("KWNEWS", "https://www.kwnews.co.kr/page/view/2026031116255017225"),
            "\uac15\uc6d0\uc77c\ubcf4",
        )

    def test_normalize_press_label_maps_bokuennews_host(self):
        self.assertEqual(
            main.normalize_press_label("bokuennews", "http://www.bokuennews.com/news/article.html?no=274896"),
            "보건신문",
        )

    def test_rss_pub_to_kst_parses_plain_site_timestamp(self):
        parsed = main._rss_pub_to_kst("2026-03-11 11:17:53")
        self.assertIsNotNone(parsed)
        self.assertEqual(parsed.tzinfo, main.KST)
        self.assertEqual(parsed.strftime("%Y-%m-%d %H:%M:%S"), "2026-03-11 11:17:53")

    def test_supply_underfill_backfill_keeps_shock_issue_story(self):
        anchor = self._make_article(
            "supply",
            "“고랭지채소 가격 안정”…강원 농산물수급관리센터 가동",
            "광역 수급관리센터 가동으로 고랭지채소 가격 안정과 재배면적 관리에 나선 기사다.",
            "https://www.seoul.co.kr/news/society/2026/03/10/20260310500115?wlog_tag3=naver",
        )
        issue = self._make_article(
            "supply",
            "[취재수첝] 샤인머스캣 실질적인 대책 서둘러라",
            "샤인머스캣 생산과잉과 미숙과, 제값 회복 대책이 시급하다는 분석 기사다.",
            "https://www.nongmin.com/article/20260309500634",
        )
        shock = self._make_article(
            "supply",
            "대형 산불에 기후변화까지…과수 묘목 품귀에 농가 울상",
            "산불과 기후변화 여파로 과수 묘목 품귀가 이어지며 농가 부담이 커졌다는 현장 기사다.",
            "https://news.kbs.co.kr/news/pc/view/view.do?ncd=8506106",
        )
        anchor.score = 36.12
        issue.score = 25.69
        shock.score = 17.42

        picked = main.select_top_articles([anchor, issue, shock], "supply", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(issue.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertIn(shock.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_dist_underfill_backfill_keeps_local_field_profile_story(self):
        core = self._make_article(
            "dist",
            "가락·구리 시장 동시휴업…딸기 산지 폐기량 2배 늘고 경락값 ‘뚝’",
            "가락시장과 구리시장이 동시에 휴업하면서 딸기 가격과 출하량이 크게 흔들렸다는 현장 기사다.",
            "https://www.nongmin.com/article/20260309500761",
        )
        systemic = self._make_article(
            "dist",
            "수도권 도매시장 첫 동시 휴업···출하쏠림에 과채류 가격 '휘청'",
            "수도권 도매시장 동시 휴업으로 출하가 몰리며 과채류 가격이 흔들리고 산지 출하 농민 불안이 커졌다는 현장 기사다.",
            "https://www.agrinet.co.kr/news/articleView.html?idxno=402440",
        )
        local = self._make_article(
            "dist",
            "지역경제 선도하는 품목 농협 - 대경사과 원예농협",
            "대경사과원예농협이 공동선별과 산지유통, 판로 확대 등 경제사업으로 지역경제를 선도한다는 현장 기사다.",
            "http://www.wonyesanup.co.kr/news/articleView.html?idxno=64002",
        )
        core.score = 48.41
        systemic.score = 36.49
        local.score = 3.70

        picked = main.select_top_articles([core, systemic, local], "dist", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(systemic.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertIn(local.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_dist_export_hub_duplicate_gives_way_to_field_profile_story(self):
        interview = self._make_article(
            "dist",
            "“K푸드를 제2 반도체로… 짝퉁 근절하고 수출 시장 다변화”",
            "aT 사장 인터뷰 형식으로 K-푸드 수출 전략과 현장 지원 방향을 다룬 기사다.",
            "https://www.donga.com/news/Economy/article/all/20260311/133511391/2",
        )
        hub_brief = self._make_article(
            "dist",
            "수출길 막히면 바로 해결...aT ,'K-푸드 원스톱 수출 지원 허브' 지원",
            "aT가 K-푸드 수출 기업의 애로사항을 바로 해결하기 위한 원스톱 수출지원 허브를 운영한다고 밝혔다.",
            "https://www.ajunews.com/view/20260311132644532",
        )
        hub_dup = self._make_article(
            "dist",
            "‘K-푸드 원스톱 수출지원 허브’ 운영",
            "농식품부와 aT가 관계부처와 함께 K-푸드 원스톱 수출지원 허브를 운영한다고 밝힌 기사다.",
            "http://www.wonyesanup.co.kr/news/articleView.html?idxno=63972",
        )
        field = self._make_article(
            "dist",
            "지역경제 선도하는 품목 농협 - 대경사과 원예농협",
            "대경사과원예농협이 공동선별과 산지유통, 판로 확대 등 경제사업으로 지역경제를 선도한다는 현장 기사다.",
            "http://www.wonyesanup.co.kr/news/articleView.html?idxno=64002",
        )
        interview.score = 23.21
        hub_brief.score = 21.66
        hub_dup.score = 14.76
        field.score = 3.70

        picked = main.select_top_articles([interview, hub_brief, hub_dup, field], "dist", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(field.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertEqual(
            int(hub_brief.link in picked_links) + int(hub_dup.link in picked_links),
            1,
            msg=str([(x.link, x.score, x.title) for x in picked]),
        )

    def test_policy_underfill_backfill_keeps_export_support_brief_story(self):
        official = self._make_article(
            "policy",
            "부여군, 농산물 가격 안정 지원… 수박 재배 농가 신청 접수",
            "부여군이 수박 재배 농가를 대상으로 가격 안정 지원 정책 신청을 받는다는 기사다.",
            "http://www.aflnews.co.kr/news/articleView.html?idxno=316205",
        )
        proposal = self._make_article(
            "policy",
            "농산물 '가격 폭락 때 유통비 지원' '최소가격 보전제' 제안 눈길",
            "농산물 가격 폭락 시 유통비 지원과 최소가격 보전제 도입 제안을 다룬 정책 기사다.",
            "https://www.newsis.com/view/NISX20260311_0003543176",
        )
        macro = self._make_article(
            "policy",
            "2월 농축산물 물가 1.4% 상승… 전체 평균 밑돌며 '안정세'",
            "농축산물 물가 동향과 정책 대응 여건을 짚는 기사다.",
            "http://www.youngnong.co.kr/news/articleView.html?idxno=58015",
        )
        export_tail = self._make_article(
            "policy",
            "송미령 농식품부 장관 “K-푸드 수출 160억불…유통 개혁·AI 접목”",
            "농식품부 장관이 K-푸드 수출 확대와 유통 개혁, AI 접목, 수출 지원 계획을 설명한 정책 브리프 기사다.",
            "https://cooknchefnews.com/news/view/1065603268596477",
        )
        official.score = 24.10
        proposal.score = 21.34
        macro.score = 18.05
        export_tail.score = 8.00

        picked = main.select_top_articles([official, proposal, macro, export_tail], "policy", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(export_tail.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertTrue(all((x.link != export_tail.link) or (not x.is_core) for x in picked))

    def test_dist_local_field_profile_is_not_treated_as_local_brief(self):
        title = "지역경제 선도하는 품목 농협 - 대경사과 원예농협"
        desc = "대경사과원예농협은 지도, 구매, 유통, 가공을 총망라하는 109년 전통의 국내 최대 과수 전문 품목농협이다. 조합원 실익 증진과 지역경제 선도에 힘쓰는 현장 기사다."
        self.assertTrue(main.is_dist_local_field_profile_context(title, desc))
        self.assertFalse(main.is_local_brief_text(title, desc, "dist"))

    def test_press_name_from_url_maps_known_korean_names(self):
        self.assertEqual(main.press_name_from_url("https://cooknchefnews.com/news/view/1065603268596477"), "쿡앤셰프")
        self.assertEqual(main.press_name_from_url("https://www.jnilbo.com/news/articleView.html?idxno=1"), "진일보")
        self.assertEqual(main.press_name_from_url("http://www.breaknews.com/123"), "브레이크뉴스")

    def test_policy_export_support_brief_excludes_generic_seminar_story(self):
        title = "글로벌 농식품 규정 변화 대응 세미나 개최"
        desc = "농식품 수출 대응을 위한 세미나 개최 소식으로, 장관 브리핑이나 정부 업무계획 설명은 없는 행사성 기사다."
        self.assertFalse(main.is_policy_export_support_brief_context(title, desc, "wonyesanup.co.kr", "원예산업신문"))

    def test_policy_event_tail_yields_to_export_support_brief(self):
        official = self._make_article(
            "policy",
            "부여군, 농산물 가격 안정 지원… 수박 재배 농가 신청 접수",
            "부여군이 수박 재배 농가를 대상으로 가격 안정 지원 정책 신청을 받는다는 기사다.",
            "http://www.aflnews.co.kr/news/articleView.html?idxno=316205",
        )
        proposal = self._make_article(
            "policy",
            "농산물 '가격 폭락 때 유통비 지원' '최소가격 보전제' 제안 눈길",
            "농산물 가격 폭락 시 유통비 지원과 최소가격 보전제 도입 제안을 다룬 정책 기사다.",
            "https://www.newsis.com/view/NISX20260311_0003543176",
        )
        macro = self._make_article(
            "policy",
            "2월 농축산물 물가 1.4% 상승… 전체 평균 밑돌며 '안정세'",
            "농축산물 물가 동향과 정책 대응 여건을 짚는 기사다.",
            "http://www.youngnong.co.kr/news/articleView.html?idxno=58015",
        )
        export_tail = self._make_article(
            "policy",
            "송미령 농식품부 장관 “K-푸드 수출 160억불…유통 개혁·AI 접목”",
            "농식품부 장관이 K-푸드 수출 확대와 유통 개혁, AI 접목, 수출 지원 계획을 설명한 정책 브리프 기사다.",
            "https://cooknchefnews.com/news/view/1065603268596477",
        )
        seminar = self._make_article(
            "policy",
            "글로벌 농식품 규정 변화 대응 세미나 개최",
            "농식품부가 유럽 포장 규정 대응 세미나를 열고 1:1 상담과 컨설팅을 진행한 행사성 기사다.",
            "http://www.wonyesanup.co.kr/news/articleView.html?idxno=63974",
        )
        official.score = 24.10
        proposal.score = 21.34
        macro.score = 18.05
        export_tail.score = 8.00
        seminar.score = 9.05

        picked = main.select_top_articles([official, proposal, macro, export_tail, seminar], "policy", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(export_tail.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertNotIn(seminar.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_dist_market_ops_context_matches_online_wholesale_tf_story(self):
        title = "온라인도매시장 제도개선·활성화 TF 운영 논의"
        desc = "aT가 시장관리운영위원회를 열고 온라인도매시장 내실화와 이용자 신뢰 제고, 거래실적 전수조사, 제도개선 및 활성화 방안을 논의한 기사다."
        self.assertTrue(main.is_dist_market_ops_context(title, desc, "wonyesanup.co.kr", "원예산업신문"))

    def test_dist_underfill_adds_online_wholesale_ops_story(self):
        interview = self._make_article(
            "dist",
            "“K푸드를 제2 반도체로… 짝퉁 근절하고 수출시장 다변화”",
            "aT 사장 인터뷰에서 K-푸드 수출시장 다변화, 유통 구조 개선, 온라인 도매시장, 직거래 플랫폼 등 현장 과제를 설명했다.",
            "https://www.donga.com/news/Economy/article/all/20260311/133511391/2",
        )
        hub_brief = self._make_article(
            "dist",
            "수출 길 막히면 바로 해결...aT ,'K-푸드 원스톱 수출 지원 허브' 지원",
            "aT가 K-푸드 수출 기업의 애로사항을 바로 해결하기 위한 원스톱 수출지원 허브를 운영한다고 밝혔다.",
            "https://www.ajunews.com/view/20260311132644532",
        )
        field = self._make_article(
            "dist",
            "지역경제 선도하는 품목 농협 - 대경사과 원예농협",
            "대경사과원예농협이 공동선별과 산지유통, 판로 확대 등 경제사업으로 지역경제를 선도한다는 현장 기사다.",
            "http://www.wonyesanup.co.kr/news/articleView.html?idxno=64002",
        )
        market_ops = self._make_article(
            "dist",
            "온라인도매시장 제도개선·활성화 TF 운영 논의",
            "aT가 시장관리운영위원회를 열고 온라인도매시장 내실화와 이용자 신뢰 제고, 거래실적 전수조사, 제도개선 및 활성화 방안을 논의한 기사다.",
            "http://www.wonyesanup.co.kr/news/articleView.html?idxno=63971",
        )
        interview.score = 23.21
        hub_brief.score = 21.66
        field.score = 3.10
        market_ops.score = 2.62

        picked = main.select_top_articles([interview, hub_brief, field, market_ops], "dist", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(field.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertIn(market_ops.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertNotIn(hub_brief.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertEqual(len(picked), 3, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_supply_feature_issue_recognizes_citrus_tariff_pressure_story(self):
        title = "미국산 만다린 관세 철폐와 제주 감귤 산업"
        desc = "미국산 만다린 무관세는 소비자에게 좋은 대안을 제시할 수 있지만, 제주도 감귤 산업에 큰 타격을 입힐 수도 있다. 정부의 적절한 대응과 제주 감귤 산업의 자체적 노력이 필요한 시점이다."
        self.assertEqual(main.supply_issue_context_bucket(title, desc), "commodity_issue")
        self.assertEqual(main.supply_feature_context_kind(title, desc), "issue")

    def test_dist_supply_management_center_context_matches_center_story(self):
        title = "강원도 농산물 광역수급관리센터 개소…배추·무 수급 선제 관리"
        desc = "강원특별자치도가 농산물 광역수급관리센터 개소식을 열고 채소류 수급 관리 시범사업을 시작했다."
        self.assertTrue(main.is_dist_supply_management_center_context(title, desc))

    def test_dist_sales_channel_ops_context_matches_joint_sales_workshop(self):
        title = "강원농협, 연합판매사업 직거래 평가회·활성화 워크숍 개최"
        desc = "농협 강원본부는 연합판매사업 직거래 평가회 및 활성화 워크숍을 열고 농가 판로 확대 방안을 점검했다."
        self.assertTrue(main.is_dist_sales_channel_ops_context(title, desc))

    def test_dist_selection_keeps_center_and_sales_channel_ops_stories(self):
        export_field = self._make_article(
            "dist",
            "K-푸드 수출 막는 비관세장벽 현장에서 푼다…농식품부, 수출업계 간담회",
            "부여 인삼공사 공장에서 현장간담회…딸기·배 수출 애로 해결 사례 공유",
            "https://www.etoday.co.kr/news/view/2564743",
        )
        field_profile = self._make_article(
            "dist",
            "밀양 무안농협, 농가조직화·품질 제고로 판매사업 성과",
            "농가조직화와 품질 제고를 통해 판매사업 성과를 낸 현장 기사다.",
            "https://www.nongmin.com/article/20260311500561",
        )
        online_ops = self._make_article(
            "dist",
            "온라인도매시장 제도개선·활성화 TF 운영 논의",
            "aT가 온라인도매시장 제도개선 TF를 열고 거래실적과 개선방안을 논의했다.",
            "http://www.amnews.co.kr/news/articleView.html?idxno=71432",
        )
        center = self._make_article(
            "dist",
            "강원도 농산물 광역수급관리센터 개소…배추·무 수급 선제 관리",
            "강원특별자치도가 농산물 광역수급관리센터 개소식을 열고 채소류 수급 관리 시범사업을 시작했다.",
            "https://www.nongmin.com/article/20260312500218",
        )
        sales_ops = self._make_article(
            "dist",
            "강원농협, 연합판매사업 직거래 평가회·활성화 워크숍 개최",
            "농협 강원본부는 연합판매사업 직거래 평가회 및 활성화 워크숍을 열고 농가 판로 확대 방안을 점검했다.",
            "https://www.news1.kr/local/kangwon/6099371",
        )
        export_field.score = 9.47
        field_profile.score = 10.05
        online_ops.score = 14.57
        center.score = 13.60
        sales_ops.score = 8.40

        picked = main.select_top_articles([export_field, field_profile, online_ops, center, sales_ops], "dist", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(center.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))
        self.assertIn(sales_ops.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_pest_same_region_duplicate_prefers_single_story(self):
        brief = self._make_article(
            "pest",
            "예산군농업기술센터, 과수화상병 사전방제 적극 홍보",
            "예산군농업기술센터가 과수화상병 확산을 막기 위해 사과·배 재배 농가를 대상으로 사전방제 약제를 공급한다.",
            "http://www.chungnamilbo.co.kr/news/articleView.html?idxno=877506",
        )
        exec_story = self._make_article(
            "pest",
            "예산군농업기술센터, 과수화상병 확산 차단 총력… 방제약제 무상 공급",
            "예산군농업기술센터가 과수화상병 예방을 위해 사과와 배 재배 농가에 방제 약제를 무상 공급한다.",
            "http://www.aflnews.co.kr/news/articleView.html?idxno=316282",
        )
        other_region = self._make_article(
            "pest",
            "수원시, 과수화상병 확산 대응 총력",
            "수원시가 사과·배 재배 농가 대상 방제 약제를 배부하며 과수화상병 대응에 나섰다.",
            "https://www.agrinet.co.kr/news/articleView.html?idxno=402500",
        )
        brief.score = 19.4
        exec_story.score = 21.1
        other_region.score = 18.7

        picked = main.select_top_articles([brief, exec_story, other_region], "pest", 5)
        picked_links = {x.link for x in picked}
        self.assertEqual(
            int(brief.link in picked_links) + int(exec_story.link in picked_links),
            1,
            msg=str([(x.link, x.score, x.title) for x in picked]),
        )
        self.assertIn(other_region.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_supply_trade_pressure_story_with_policy_topic_is_selected(self):
        story = self._make_article(
            "supply",
            "[생글기자 코너] 미국산 만다린 관세 철폐와 제주 감귤 산업",
            "[생글기자 코너] 미국산 만다린 관세 철폐와 제주 감귤 산업, 미국산 만다린 무관세는 소비자에게 좋은 대안을 제시할 수 있지만, 제주도 감귤 산업에 큰 타격을 입힐 수도 있다. 정부의 적절한 대응과 제주 감귤 산업의 자체적 노력이 필요한 시점이다.",
            "https://www.hankyung.com/article/2026030632081",
        )
        peer = self._make_article(
            "supply",
            "사과 값 고공행진에 묘목도 '불티'…30% 이상 가격 급등",
            "사과 가격 급등 여파로 묘목 수요와 가격이 함께 오르며 농가 부담이 커졌다는 기사다.",
            "https://www.yna.co.kr/view/AKR20260313000000000",
        )
        story.topic = "정책"
        story.score = 31.44
        peer.score = 28.94

        picked = main.select_top_articles([story, peer], "supply", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(story.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_remote_foreign_shipping_story_is_blocked(self):
        title = "유가에 놀란 백악관, '美선박만 美항구간 운송' 일시면제 검토"
        desc = "미국 백악관이 연안 운송 규제를 한시 완화하는 방안을 검토 중이라는 외신 기사다."
        self.assertTrue(main.is_remote_foreign_trade_brief_context(title, desc, "sbs.co.kr"))
        self.assertFalse(
            main.is_relevant(
                title,
                desc,
                "sbs.co.kr",
                "https://news.sbs.co.kr/news/endPage.do?news_id=N1008044518",
                next(s for s in main.SECTIONS if s["key"] == "dist"),
                "SBS",
            )
        )

    def test_global_reassign_moves_supply_center_story_from_policy_to_dist(self):
        title = "강원도 ‘농산물 광역수급관리센터’ 개소…배추·무 수급 선제 관리"
        desc = "강원특별자치도가 농산물 광역수급관리센터 개소식을 열고 채소류 수급 관리 시범사업을 시작했다."
        url = "https://www.nongmin.com/article/20260312500218"
        a = self._make_article("policy", title, desc, url)
        a.score = 38.71
        raw = {"policy": [a], "supply": [], "dist": [], "pest": []}

        moved = main._global_section_reassign(raw, self.now, self.now)

        self.assertGreaterEqual(moved, 1)
        self.assertFalse(raw["policy"], msg=str([(x.section, x.link, x.score) for x in raw["policy"]]))
        self.assertEqual(len(raw["dist"]), 1, msg=str([(x.section, x.link, x.score) for x in raw["dist"]]))
        self.assertEqual(raw["dist"][0].link, url)

    def test_dist_selection_keeps_export_resolution_story_with_outlier_present(self):
        center = self._make_article(
            "dist",
            "강원도 ‘농산물 광역수급관리센터’ 개소…배추·무 수급 선제 관리",
            "강원특별자치도가 농산물 광역수급관리센터 개소식을 열고 채소류 수급 관리 시범사업을 시작했다.",
            "https://www.nongmin.com/article/20260312500218",
        )
        disruption = self._make_article(
            "dist",
            "가락시장 토요일 휴업, 농산물 시세 하락 부추겼나",
            "가락시장 운영 차질로 농산물 시세 하락 우려를 짚는 기사다.",
            "https://www.ikpnews.net/news/articleView.html?idxno=99999",
        )
        sales_ops = self._make_article(
            "dist",
            "강원농협, '연합판매사업 직거래 평가회·활성화 워크숍' 개최",
            "농협 강원본부가 연합판매사업 직거래 평가회와 활성화 워크숍을 열어 농가 판로 확대를 점검했다.",
            "https://www.news1.kr/local/kangwon/6099371",
        )
        market_ops = self._make_article(
            "dist",
            "온라인도매시장 제도개선·활성화 TF 운영 논의",
            "aT가 온라인도매시장 제도개선 TF를 열고 거래실적과 개선방안을 논의했다.",
            "http://www.amnews.co.kr/news/articleView.html?idxno=71432",
        )
        export_resolution = self._make_article(
            "dist",
            "K-푸드 수출 막는 ‘비관세장벽’ 현장에서 푼다…농식품부, 수출업계 간담회",
            "부여 인삼공사 공장에서 현장간담회…딸기·배 수출 애로 해결 사례 공유, N-데스크를 통한 상시 애로 접수 내용을 담았다.",
            "https://www.etoday.co.kr/news/view/2564743",
        )
        center.score = 30.54
        disruption.score = 19.28
        sales_ops.score = 11.10
        market_ops.score = 12.87
        export_resolution.score = 12.64

        picked = main.select_top_articles([center, disruption, sales_ops, market_ops, export_resolution], "dist", 5)
        picked_links = {x.link for x in picked}
        self.assertIn(export_resolution.link, picked_links, msg=str([(x.link, x.score, x.title) for x in picked]))

    def test_dist_sales_channel_roundups_are_treated_as_same_story(self):
        news_story = self._make_article(
            "dist",
            "강원농협, '연합판매사업 직거래 평가회·활성화 워크숍' 개최",
            "농협 강원본부가 연합판매사업 직거래 평가회와 활성화 워크숍을 열어 농가 판로 확대를 점검했다.",
            "https://www.news1.kr/local/kangwon/6099371",
        )
        wire_story = self._make_article(
            "dist",
            "강원 농협, 2026년 연합판매사업 활성화 워크숍 개최",
            "강원 농협이 연합판매사업 활성화 워크숍과 직거래 평가회를 열었다는 기사다.",
            "https://www.yna.co.kr/view/AKR20260312000000062",
        )
        photo_story = self._make_article(
            "dist",
            "[포토뉴스]2026년 강원 농협 연합판매사업 직거래 평가회 및 활성화 워크숍",
            "강원 농협의 연합판매사업 직거래 평가회 현장을 담은 포토 기사다.",
            "https://www.kwnews.co.kr/page/view/20260312000000000",
        )
        other = self._make_article(
            "dist",
            "온라인도매시장 제도개선·활성화 TF 운영 논의",
            "aT가 온라인도매시장 제도개선 TF를 열고 거래실적과 개선방안을 논의했다.",
            "http://www.amnews.co.kr/news/articleView.html?idxno=71432",
        )
        news_story.score = 11.10
        wire_story.score = 14.24
        photo_story.score = 13.14
        other.score = 12.87

        self.assertTrue(main._is_similar_story(news_story, wire_story, "dist"))
        self.assertTrue(main._is_similar_story(photo_story, wire_story, "dist"))

    def test_flower_novelty_noise_is_rejected_from_supply_and_policy(self):
        title = "유재석도 받은 '이 꽃다발'…졸업 선물로 뜬 레고 보태니컬"
        desc = "레고 꽃다발과 보태니컬 시리즈가 시상식 선물과 소비 트렌드로 주목받는다는 기사다."
        url = "https://example.com/lego-bouquet"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        self.assertFalse(main.is_relevant(title, desc, dom, url, self.conf["supply"], press))
        self.assertFalse(main.is_relevant(title, desc, dom, url, self.conf["policy"], press))

    def test_flower_novelty_noise_with_hwae_association_mentions_is_still_rejected(self):
        title = "유재석 꽃다발 논란…화원협회 '화훼 농가 또 다른 상처'"
        desc = "화원협회가 시상식 레고 꽃다발 논란을 두고 화훼 농가 생존권과 소비 촉진 정책을 언급한 기사다."
        self.assertTrue(main.is_flower_novelty_noise_context(title, desc))

    def test_flower_novelty_noise_catches_toy_flower_policy_story(self):
        title = "장난감 꽃, 화훼 농가 생존권 위협"
        desc = "생화 너무 비싸 장난감 꽃 시장이 커진다는 내용으로 화훼 농가 생존권 우려를 담은 기사"
        self.assertTrue(main.is_flower_novelty_noise_context(title, desc))

    def test_postbuild_audit_drops_toy_flower_policy_story(self):
        article = self._make_article(
            "policy",
            "장난감 꽃, 화훼 농가 생존권 위협",
            "생화 너무 비싸 장난감 꽃 시장이 커진다는 내용으로 화훼 농가 생존권 우려를 담은 기사",
            "https://www.seoul.co.kr/news/society/2026/01/12/20260112010005?wlog_tag3=naver",
        )
        self.assertEqual(main._postbuild_article_reject_reason(article, "policy"), "flower_novelty_noise")

    def test_postbuild_audit_updates_debug_selected_flag(self):
        article = self._make_article(
            "policy",
            "장난감 꽃, 화훼 농가 생존권 위협",
            "생화 너무 비싸 장난감 꽃 시장이 커진다는 내용으로 화훼 농가 생존권 우려를 담은 기사",
            "https://www.seoul.co.kr/news/society/2026/01/12/20260112010005?wlog_tag3=naver",
        )
        original = dict(main.DEBUG_DATA)
        try:
            main.DEBUG_DATA["sections"] = {
                "policy": {
                    "total_selected": 1,
                    "top": [
                        {
                            "selected": True,
                            "is_core": True,
                            "title": article.title[:160],
                            "url": article.originallink[:500],
                            "reason": "",
                        }
                    ],
                }
            }
            main._mark_debug_postbuild_reject("policy", article, "flower_novelty_noise")
            row = main.DEBUG_DATA["sections"]["policy"]["top"][0]
            self.assertFalse(row["selected"])
            self.assertEqual(row["reason"], "flower_novelty_noise")
            self.assertEqual(main.DEBUG_DATA["sections"]["policy"]["total_selected"], 0)
        finally:
            main.DEBUG_DATA.clear()
            main.DEBUG_DATA.update(original)

    def test_sync_debug_with_final_sections_marks_pruned_rows(self):
        article = self._make_article(
            "policy",
            "장난감 꽃, 화훼 농가 생존권 위협",
            "생화 너무 비싸 장난감 꽃 시장이 커진다는 내용으로 화훼 농가 생존권 우려를 담은 기사",
            "https://www.seoul.co.kr/news/society/2026/01/12/20260112010005?wlog_tag3=naver",
        )
        original = dict(main.DEBUG_DATA)
        try:
            main.DEBUG_DATA["sections"] = {
                "policy": {
                    "total_selected": 1,
                    "top": [
                        {
                            "selected": True,
                            "is_core": True,
                            "title": article.title[:160],
                            "url": article.originallink[:500],
                            "reason": "",
                        }
                    ],
                }
            }
            main._sync_debug_with_final_sections({"policy": []})
            row = main.DEBUG_DATA["sections"]["policy"]["top"][0]
            self.assertFalse(row["selected"])
            self.assertEqual(row["reason"], "postbuild_pruned")
            self.assertEqual(main.DEBUG_DATA["sections"]["policy"]["total_selected"], 0)
        finally:
            main.DEBUG_DATA.clear()
            main.DEBUG_DATA.update(original)

    def test_flower_market_trend_with_agri_context_still_prefers_supply(self):
        title = "졸업식 대목 앞둔 꽃시장…절화 경매가 오르고 화훼 농가 기대"
        desc = "졸업식 성수기를 앞두고 꽃시장 절화 경매가 상승하고 화훼 농가 출하가 늘고 있다는 현장 기사다."
        best, scores = self._best_section(title, desc, "https://example.com/flower-market")
        self.assertEqual(best, "supply", msg=f"scores={scores}")

    def test_flower_supply_registry_avoids_lifestyle_bouquet_queries(self):
        flower_entry = next(entry for entry in main.COMMODITY_REGISTRY if entry.get("topic") == "화훼")
        joined = " ".join(flower_entry.get("supply_queries") or [])
        self.assertNotIn("레고", joined)
        self.assertNotIn("꽃다발 선물", joined)
        self.assertIn("화훼 경매", joined)
        self.assertIn("화훼공판장 경매", joined)

    def test_recall_fallback_queries_expand_with_generic_archive_safe_queries(self):
        supply_queries, _ = main._build_recall_fallback_queries("supply", self.conf["supply"], [], 99.0, report_date="2026-01-12")
        policy_queries, _ = main._build_recall_fallback_queries("policy", self.conf["policy"], [], 99.0, report_date="2026-01-05")
        dist_queries, _ = main._build_recall_fallback_queries("dist", self.conf["dist"], [], 99.0, report_date="2026-01-05")
        pest_queries, _ = main._build_recall_fallback_queries("pest", self.conf["pest"], [], 99.0, report_date="2026-01-05")

        self.assertIn("농산물 가격 동향", main._recall_common_queries("supply", "2026-01-12"))
        self.assertTrue(len(supply_queries) > 0)
        self.assertIn("농식품부 농산물 수급 점검", policy_queries)
        self.assertIn("도매시장 경매", dist_queries)
        self.assertIn("과수화상병 예찰", main._recall_common_queries("pest", "2026-01-05"))
        self.assertTrue(len(pest_queries) > 0)

    def test_web_recall_queries_follow_fallback_then_common_registry(self):
        recall_meta = {}
        queries = main._build_web_recall_queries("dist", ["산지유통센터", "도매시장 경매"], recall_meta)
        self.assertEqual(queries[:2], ["산지유통센터", "도매시장 경매"])
        self.assertIn("web_queries", recall_meta)
        self.assertLessEqual(len(queries), main.WEB_RECALL_QUERY_CAP_PER_SECTION)

    def test_reset_debug_report_clears_previous_state(self):
        original_debug = main.DEBUG_REPORT
        original_data = {
            "generated_at_kst": main.DEBUG_DATA.get("generated_at_kst"),
            "build_tag": main.DEBUG_DATA.get("build_tag"),
            "filter_rejects": list(main.DEBUG_DATA.get("filter_rejects", [])),
            "sections": dict(main.DEBUG_DATA.get("sections", {})),
            "collections": dict(main.DEBUG_DATA.get("collections", {})),
        }
        try:
            main.DEBUG_REPORT = True
            main.DEBUG_DATA["filter_rejects"] = [{"reason": "old"}]
            main.DEBUG_DATA["sections"] = {"supply": {"total_selected": 9}}
            main.DEBUG_DATA["collections"] = {"supply": {"queries": ["old"]}}
            main.reset_debug_report()
            self.assertEqual(main.DEBUG_DATA["filter_rejects"], [])
            self.assertEqual(main.DEBUG_DATA["sections"], {})
            self.assertEqual(main.DEBUG_DATA["collections"], {})
            self.assertTrue(main.DEBUG_DATA["generated_at_kst"])
        finally:
            main.DEBUG_REPORT = original_debug
            main.DEBUG_DATA["generated_at_kst"] = original_data["generated_at_kst"]
            main.DEBUG_DATA["build_tag"] = original_data["build_tag"]
            main.DEBUG_DATA["filter_rejects"] = original_data["filter_rejects"]
            main.DEBUG_DATA["sections"] = original_data["sections"]
            main.DEBUG_DATA["collections"] = original_data["collections"]

class TestRecentItemsRebuild(unittest.TestCase):
    def test_rebuild_recent_items_replaces_same_day_entries(self):
        base_day = datetime(2026, 3, 3, tzinfo=main.KST).date()
        report_date = "2026-03-03"
        existing = [
            {"date": "2026-03-03", "canon": "https://old.example.com/a", "norm": "url:old-a"},
            {"date": "2026-03-02", "canon": "https://keep.example.com/b", "norm": "url:keep-b"},
        ]

        a = main.Article(
            section="pest",
            title="진주시, 과수화상병 방제 총력",
            description="과원 예찰과 약제 방제를 실시한다.",
            link="https://www.newsis.com/view/NISX20260228_0003530198",
            originallink="https://www.newsis.com/view/NISX20260228_0003530198",
            pub_dt_kst=datetime(2026, 3, 2, tzinfo=main.KST),
            domain=main.domain_of("https://www.newsis.com/view/NISX20260228_0003530198"),
            press="뉴시스",
            title_key=main.norm_title_key("진주시, 과수화상병 방제 총력"),
            canon_url=main.canonicalize_url("https://www.newsis.com/view/NISX20260228_0003530198"),
            norm_key=main.make_norm_key(main.canonicalize_url("https://www.newsis.com/view/NISX20260228_0003530198"), "뉴시스", main.norm_title_key("진주시, 과수화상병 방제 총력")),
            topic="병해충",
            score=10.0,
        )
        by_section = {"supply": [], "policy": [], "dist": [], "pest": [a]}

        rebuilt = main.rebuild_recent_items_for_report_date(existing, by_section, report_date, base_day)

        self.assertFalse(any((it.get("date") == report_date and it.get("canon") == "https://old.example.com/a") for it in rebuilt))
        self.assertTrue(any(it.get("canon") == "https://keep.example.com/b" for it in rebuilt))
        self.assertTrue(any(it.get("canon") == main.canonicalize_url("https://www.newsis.com/view/NISX20260228_0003530198") for it in rebuilt))

    def test_rebuild_recent_items_handles_missing_by_section(self):
        base_day = datetime(2026, 3, 3, tzinfo=main.KST).date()
        report_date = "2026-03-03"
        existing = [
            {"date": "2026-03-03", "canon": "https://old.example.com/a", "norm": "url:old-a"},
            {"date": "2026-03-01", "canon": "https://keep.example.com/c", "norm": "url:keep-c"},
        ]

        rebuilt = main.rebuild_recent_items_for_report_date(existing, None, report_date, base_day)

        self.assertFalse(any(it.get("date") == report_date for it in rebuilt))
        self.assertTrue(any(it.get("canon") == "https://keep.example.com/c" for it in rebuilt))

if __name__ == "__main__":
    unittest.main()
