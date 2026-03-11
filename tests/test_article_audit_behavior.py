import unittest
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main


class TestArticleAuditBehavior(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.conf = {section["key"]: section for section in main.SECTIONS}
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

    def test_mt_political_apology_story_is_not_treated_as_apple_article(self):
        title = '한병도 "尹 반대 결의문, 반쪽짜리 사과 …장동혁 입장 밝혀라"'
        desc = "한병도 원내대표가 정치적 사안에 대해 입장을 밝혀야 한다고 강조하며, 에너지 수급과 가격 동향 대응 TF 출범 소식을 전했다."
        url = "https://www.mt.co.kr/politics/2026/03/10/2026031009405991292"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)

        self.assertTrue(main.is_apple_apology_context(f"{title} {desc}"))
        self.assertFalse(main.is_edible_apple_context(f"{title} {desc}"))

        scores = {}
        for key, conf in self.conf.items():
            if main.is_relevant(title, desc, dom, url, conf, press):
                scores[key] = main.compute_rank_score(title, desc, dom, self.now, conf, press)
        self.assertEqual(scores, {}, msg=str(scores))

    def test_pest_story_can_still_pass_without_title_signal_when_body_is_strong(self):
        title = "농가 긴급 대응"
        desc = "과수화상병 확산 차단을 위해 과원 전수조사와 정밀예찰, 약제 방제를 동시에 실시한다."
        url = "https://example.com/pest-body-strong"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)

        self.assertTrue(main.is_pest_story_focus_strong(title, desc))
        self.assertTrue(main.is_relevant(title, desc, dom, url, self.conf["pest"], press))

    def test_kbs_roundup_with_partial_pest_sentence_is_rejected_for_pest(self):
        title = "[여기는 원주] ‘평창컵 국제 알파인스키대회’ 개막…13일까지 외"
        desc = "평창컵 국제 알파인스키대회와 함께 과수화상병 방제를 위한 방제 면적이 131만㎡에 달하는 소식이 전해졌다. 이 바이러스는 농재배에 큰 위협이 되고 있다."
        url = "https://news.kbs.co.kr/news/pc/view/view.do?ncd=8504583"
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)

        self.assertFalse(main.is_pest_story_focus_strong(title, desc))
        self.assertFalse(main.is_relevant(title, desc, dom, url, self.conf["pest"], press))

    def test_postbuild_audit_prunes_known_false_positives(self):
        bad_supply = self._make_article(
            "supply",
            '한병도 "尹 반대 결의문, 반쪽짜리 사과 …장동혁 입장 밝혀라"',
            "한병도 원내대표가 정치적 사안에 대해 입장을 밝혀야 한다고 강조하며, 에너지 수급과 가격 동향 대응 TF 출범 소식을 전했다.",
            "https://www.mt.co.kr/politics/2026/03/10/2026031009405991292",
        )
        bad_pest = self._make_article(
            "pest",
            "[여기는 원주] ‘평창컵 국제 알파인스키대회’ 개막…13일까지 외",
            "평창컵 국제 알파인스키대회와 함께 과수화상병 방제를 위한 방제 면적이 131만㎡에 달하는 소식이 전해졌다. 이 바이러스는 농재배에 큰 위협이 되고 있다.",
            "https://news.kbs.co.kr/news/pc/view/view.do?ncd=8504583",
        )
        by_section = {"supply": [bad_supply], "policy": [], "dist": [], "pest": [bad_pest]}

        pruned = main._audit_final_sections(by_section)

        self.assertEqual(pruned, 2)
        self.assertEqual(by_section["supply"], [])
        self.assertEqual(by_section["pest"], [])
