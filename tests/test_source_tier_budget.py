"""PR-2: 최하위 매체 예산이 발행 지면까지 지켜지는지, 농협 그룹 매체가
제 티어를 받는지 검증한다.

배경: 예산(섹션당 1건·전체 4건)은 이미 있었지만 선호 카드수 리필이 예산을
보지 않아, 방금 걷어낸 저티어 카드를 그대로 되돌려 놓고 있었다. 08-10~12
지면은 그렇게 저티어 5건으로 나갔다(source_quality 60).
그리고 NBS(한국농업방송)는 어느 매체 목록에도 없어 최하 티어로 떨어졌다.
"""
import unittest
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main  # noqa: E402


def _article(section: str, title: str, url: str, press: str) -> main.Article:
    canon = main.canonicalize_url(url)
    title_key = main.norm_title_key(title)
    return main.Article(
        section=section,
        title=title,
        description=f"{title} 관련 수급·출하 동향을 다룬 기사다.",
        link=url,
        originallink=url,
        pub_dt_kst=datetime.now(main.KST),
        domain=main.domain_of(url),
        press=press,
        norm_key=main.make_norm_key(canon, press, title_key),
        title_key=title_key,
        canon_url=canon,
        topic="",
        score=20.0,
    )


class LowTierBudgetTests(unittest.TestCase):
    def test_publish_sweep_never_shrinks_a_section(self) -> None:
        """빈 슬롯은 독자품질 점수를 95로 캡한다 — 저티어 한 건보다 비싸다."""
        section = [
            _article("dist", f"미상매체 유통 기사 {idx}", f"https://unknown-outlet-{idx}.com/n/{idx}", "미상")
            for idx in range(main.MIN_FALLBACK_PER_SECTION + 2)
        ]
        for article in section:
            self.assertTrue(main._is_final_low_tier_source(article))

        shrinkable = {"supply": [], "policy": [], "dist": list(section), "pest": []}
        main._cap_final_low_tier_sources(shrinkable, {"dist": []}, allow_drop=True)
        self.assertLess(len(shrinkable["dist"]), len(section))

        preserved = {"supply": [], "policy": [], "dist": list(section), "pest": []}
        main._cap_final_low_tier_sources(preserved, {"dist": []}, allow_drop=False)
        self.assertEqual(len(preserved["dist"]), len(section))

    def test_refill_deprioritises_low_tier_once_the_budget_is_spent(self) -> None:
        final_by_section = {
            "supply": [_article("supply", f"저티어 수급 기사 {i}", f"https://low-{i}.com/n/{i}", "미상") for i in range(4)],
            "policy": [],
            "dist": [],
            "pest": [],
        }
        spent = sum(
            1
            for items in final_by_section.values()
            for a in items
            if main._is_final_low_tier_source(a)
        )
        self.assertGreaterEqual(spent, main.FINAL_LOW_TIER_MAX_TOTAL)

        trusted = _article("supply", "연합뉴스 배추 출하 동향", "https://www.yna.co.kr/view/1", "연합뉴스")
        cheap = _article("supply", "미상매체 배추 출하 동향", "https://low-extra.com/n/1", "미상")
        self.assertFalse(main._is_final_low_tier_source(trusted))
        self.assertTrue(main._is_final_low_tier_source(cheap))

        section_low = [a for a in final_by_section["supply"] if main._is_final_low_tier_source(a)]
        self.assertFalse(main._low_tier_section_budget_allows("supply", cheap, section_low))
        self.assertTrue(main._low_tier_section_budget_allows("supply", cheap, []))


class NhGroupMediaTests(unittest.TestCase):
    """농민신문·NBS는 농협 그룹 매체다 — 구독자에게 직접적인 정보원."""

    def test_nbs_is_recognised_by_label_and_domain(self) -> None:
        for press, domain in (
            ("NBS", "inbs.co.kr"),
            ("NBS한국농업방송", "example.com"),
            ("한국농업방송", ""),
            ("", "www.inbs.co.kr"),
        ):
            with self.subTest(press=press, domain=domain):
                self.assertTrue(main.is_nh_group_media(press, domain))
        self.assertTrue(main.is_nh_group_media("농민신문", "nongmin.com"))
        self.assertFalse(main.is_nh_group_media("연합뉴스", "yna.co.kr"))

    def test_nh_group_media_reach_the_top_press_tier(self) -> None:
        self.assertEqual(main.press_tier("NBS", "inbs.co.kr"), 3)
        self.assertEqual(main.press_tier("", "www.inbs.co.kr"), 3)
        self.assertEqual(main.press_tier("농민신문", "nongmin.com"), 3)

    def test_nbs_is_not_penalised_as_an_unknown_abbreviation(self) -> None:
        nbs = main.press_weight("NBS", "inbs.co.kr")
        unknown = main.press_weight("XYZ", "xyz-news.com")
        self.assertGreater(nbs, unknown)
        # 농업 전문지보다 조금 위, 공식 기관(tier 4)보다는 아래여야 한다.
        self.assertGreater(nbs, main.press_weight("원예산업신문", "wonyesanup.co.kr"))
        self.assertLess(nbs, main.press_weight("농식품부", "mafra.go.kr"))

    def test_inbs_domain_maps_to_a_readable_press_label(self) -> None:
        label = main.normalize_press_label(
            main.press_name_from_url("https://www.inbs.co.kr/vod/PGM002/10737/detail.do"),
            "https://www.inbs.co.kr/vod/PGM002/10737/detail.do",
        )
        self.assertIn("농업방송", label)

    def test_group_membership_does_not_excuse_a_local_chapter_event_story(self) -> None:
        """가점은 가점일 뿐 — 동정·행사 기사는 여전히 감점된다."""
        penalty = main.local_coop_penalty(
            "안성농협, 지역 어르신 초청 행사 열고 기부금 전달",
            "농민신문",
            "nongmin.com",
            "supply",
        )
        self.assertGreater(penalty, 0.0)


if __name__ == "__main__":
    unittest.main()
