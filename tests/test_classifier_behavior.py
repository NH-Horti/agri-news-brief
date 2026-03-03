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
