import unittest
from datetime import datetime
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

    def test_collect_candidates_respects_window_min_hours_for_rebuild_like_window(self):
        section_conf = {
            "key": "pest",
            "queries": ["과수화상병 방제"],
            "must_terms": ["방제", "병해충", "약제", "예찰", "과수화상병"],
        }

        # 리빌드 윈도우(직전 영업일 07:00 ~ 당일 07:00)보다 12시간 이른 기사지만,
        # WINDOW_MIN_HOURS(기본 72h) 내라면 후보 수집에서 살아야 한다.
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

        self.assertTrue(any("NISX20260228_0003530198" in (a.link or "") for a in items), msg=str([(a.link, a.pub_dt_kst) for a in items]))

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


if __name__ == "__main__":
    unittest.main()
