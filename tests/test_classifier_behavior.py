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

    def test_local_coop_export_feature_prefers_dist_over_supply(self):
        title = "경주 현곡농협, 수출 등 활발한 경제사업으로 농가실익 증진"
        desc = "경주 현곡농협이 샤인머스캣 농가의 수출을 통해 경제적 실익을 증진하고 있다. 대만으로의 수출이 예정되어 있으며, GAP 인증을 받은 농가들이 참여하고 있다."
        best, scores = self._best_section(title, desc, "https://www.nongmin.com/article/20260306500345")
        self.assertEqual(best, "dist", msg=f"scores={scores}")

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
        title = "“온종일 불때야 하는데 막막” 초록색 딸기 바라보며 한숨"
        desc = "딸기 체험 농장을 운영하는 농가가 생육적온을 맞추기 어려워 난방 부담이 커졌고 초록빛 딸기가 그대로 남아 있다고 설명했다."
        best, scores = self._best_section(title, desc, "https://www.sedaily.com/article/20017059")
        self.assertEqual(best, "supply", msg=f"scores={scores}")

    def test_fnnews_citrus_blind_test_story_prefers_supply(self):
        title = "제주 감귤, 수입산과 맛 블라인드 테스트 69% 압도"
        desc = "제주산 만감류 천혜향이 수입 만다린보다 두 배 이상 높은 소비자 선호도를 기록하며 제주 감귤의 품질 경쟁력을 입증했다."
        best, scores = self._best_section(title, desc, "https://www.fnnews.com/news/202603091837432209")
        self.assertEqual(best, "supply", msg=f"scores={scores}")

    def test_supply_selection_keeps_item_feature_story_without_price_signal(self):
        article = self._make_article(
            "supply",
            "“온종일 불때야 하는데 막막” 초록색 딸기 바라보며 한숨",
            "딸기 체험 농장을 운영하는 농가가 생육적온을 맞추기 어려워 난방비 부담이 커졌다고 밝혔다.",
            "https://www.sedaily.com/article/20017059",
        )
        picked = main.select_top_articles([article], "supply", 5)
        self.assertTrue(any(x.link == article.link for x in picked), msg=str([(x.link, x.score) for x in picked]))

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

    def test_supply_recall_fallback_queries_include_feature_signals(self):
        section_conf = {
            "key": "supply",
            "queries": ["사과 가격", "배 가격", "감귤 가격", "딸기 작황", "화훼 가격"],
            "must_terms": ["사과", "배", "감귤", "딸기", "화훼"],
        }
        queries, meta = main._build_recall_fallback_queries("supply", section_conf, [], 99.0)
        self.assertIn("감귤 품질", queries, msg=str(meta))
        self.assertIn("딸기 생육", queries, msg=str(meta))

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

    def test_low_tier_policy_source_does_not_take_core_over_major_sources(self):
        low = self._make_article(
            "policy",
            "농축산물 물가 1%대 안착, 수급 안정·할인지원에 예산 집중 투입",
            "농식품부는 농축산물 가격 안정을 위해 정부양곡을 방출하고 사과 수급 안정 대책을 이어간다.",
            "https://www.farmnmarket.com/news/article.html?no=25786",
        )
        major1 = self._make_article(
            "policy",
            "농산물 최대 50% 할인 지속…정부 '석유류·먹거리 가격 안정 총력'",
            "농림축산식품부는 농산물 가격 안정을 위해 할인 지원과 공급 안정 조치를 이어간다.",
            "https://www.nongmin.com/article/20260306500258",
        )
        major2 = self._make_article(
            "policy",
            "한은 '물가, 중동 사태 따른 국제 유가가 변수'",
            "농축수산물 물가는 안정세를 보이고 있으나 유가와 물가 불확실성이 다시 커질 수 있다.",
            "https://it.chosun.com/news/articleView.html?idxno=2023092158205",
        )

        picked = main.select_top_articles([low, major1, major2], "policy", 5)
        low_picked = next((x for x in picked if x.link == low.link), None)
        self.assertTrue(low_picked is None or (not getattr(low_picked, "is_core", False)), msg=str([(x.link, x.score, x.is_core) for x in picked]))
        self.assertTrue(any(getattr(x, "is_core", False) for x in picked if x.link in {major1.link, major2.link}), msg=str([(x.link, x.score, x.is_core) for x in picked]))

    def test_local_coop_feature_can_fill_dist_when_room_but_not_core(self):
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
        local_picked = next((x for x in picked if x.link == local.link), None)
        self.assertIsNotNone(local_picked, msg=str([(x.link, x.score, x.is_core) for x in picked]))
        self.assertFalse(getattr(local_picked, "is_core", False), msg=str([(x.link, x.score, x.is_core) for x in picked]))

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
        self.assertTrue(msg.splitlines()[0].startswith("[DEV] "), msg=msg)
        self.assertIn("개발 테스트 버전(운영 아님)", msg)


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
