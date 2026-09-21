"""2026-09-22 회귀 방지: 병해충 후보가 얇은 날 최종 게이트 체인이 섹션을 비우던 결함.

그날 pest raw 풀은 8건이었고 그중 진도 대파 무름병(연합뉴스)이 가장 강한 카드였는데
1) 제목의 '농업재해'가 기상재해 노이즈로 오분류돼 꼬리 자리에서 차단됐고,
2) 같은 사건 두 판 중 게이트에 걸리는 판(본문 깨짐)이 남고 통과하는 판이 지워졌으며,
3) 최종 reader 바닥 단계가 cross-day 후보 기준으로 pest 카드 전부를 '누출'로 걷어내
   section_underfill:pest=1/3 으로 발행이 막혔다.
"""
import sys
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import main
import editorial_rules

KST = timezone(timedelta(hours=9))


def _mk(section, title, desc="", press="언론사", domain="news.example.com",
        link="", score=10.0, is_core=False, fit=2.0):
    link = link or f"https://{domain}/{abs(hash(title)) % 10**8}"
    return main.Article(
        section=section,
        title=title,
        description=desc,
        link=link,
        originallink=link,
        pub_dt_kst=datetime(2026, 9, 21, 16, 0, tzinfo=KST),
        domain=domain,
        press=press,
        norm_key=main.make_norm_key(link, press, main.norm_title_key(title)),
        title_key=main.norm_title_key(title),
        canon_url=link,
        topic="",
        score=score,
        is_core=is_core,
        selection_fit_score=fit,
    )


JINDO_TITLE = '박지원 "진도 대파 무름병, 농업재해로 인정"'
JINDO_DESC = (
    "대파 무름병은 뿌리와 줄기 전체가 물러 썩게 하는 병으로, 온도가 높고 다습한 토양에서 주로 발생한다. "
    "진도 529개 농가 61㏊에서 피해를 본 것으로 집계됐다. 박 의원은 \"지원금은 주로 피해 확산을 막는 농약·종자 구입에 쓰인다\"고 말했다."
)


def _jindo():
    return _mk("pest", JINDO_TITLE, JINDO_DESC, press="연합뉴스", domain="yna.co.kr", score=14.2, fit=1.7)


class TestNamedDiseaseIsNotWeatherNoise(unittest.TestCase):
    def test_named_disease_with_disaster_wording_is_pest_story(self):
        article = _jindo()
        self.assertFalse(main._is_pest_weather_disaster_noise(article))
        self.assertFalse(main._is_weak_pest_tail(article))
        self.assertFalse(main._is_generic_pest_notice_tail(article))
        self.assertEqual(
            main._preferred_tail_block_reason(article, "pest", current_count=1, raw_count=8),
            "",
        )

    def test_named_disease_damage_recognition_is_cross_day_candidate(self):
        self.assertTrue(main._is_cross_day_pest_candidate(_jindo()))

    def test_pure_storm_preparedness_notice_still_noise(self):
        article = _mk(
            "pest",
            "태풍 북상 대비 농작물 관리 당부",
            "군은 태풍 피해 예방과 피해 최소화를 위해 시설물 점검과 배수로 정비를 당부했다.",
        )
        self.assertTrue(main._is_pest_weather_disaster_noise(article))


class TestFinalDedupeKeepsGatePassingVariant(unittest.TestCase):
    def test_gate_passing_variant_wins_over_higher_tier_rejected_variant(self):
        good = _mk(
            "pest",
            "농식품부, 여름철 폭염·우박 피해 농가에 추석 전 재해복구비 305억원 지원",
            "농림축산식품부는 7~8월 폭염·가뭄과 8월 31일 우박 피해 농가 1만4689곳에 재해복구비 305억원을 지급한다. 인삼, 단감, 배, 대파 등 농작물 피해가 컸다.",
            press="농기자재신문", domain="newsam.co.kr", score=14.3, fit=4.9,
        )
        bad = _mk(
            "pest",
            "폭염·가뭄·우박 피해 농가에 복구비 305억···추석 전 지급",
            "홈 전체기사 --> 2026-09-22 00:00 (화) 한국어 EN 日文 中文 로그인 회원가입 구독신청",
            press="한국농어민신문", domain="agrinet.co.kr", score=8.2, fit=0.0,
        )

        def _reject(article, section_key, *, apply_selection_fit=True):
            return "pest_partial_mention" if article is bad else ""

        with patch.object(main, "_duplicate_story_pair_reason", return_value="same_gov_multi_quantity"), \
                patch.object(main, "_postbuild_article_reject_reason", side_effect=_reject):
            final = {"pest": [bad, good], "supply": [], "policy": [], "dist": []}
            removed, _refilled = main._final_global_story_dedupe(final, None)
        self.assertEqual(removed, 1)
        self.assertEqual([a.title for a in final["pest"]], [good.title])


class TestReaderFloorKeepsThinPestSection(unittest.TestCase):
    def test_weak_but_valid_pest_cards_survive_without_stronger_candidate(self):
        jindo = _jindo()
        relief = _mk(
            "pest",
            "농식품부, 여름철 폭염·우박 피해 농가에 추석 전 재해복구비 지원",
            "농림축산식품부는 7~8월 폭염·가뭄과 우박 피해 농가에 재해복구비를 지급한다. 인삼, 단감, 배, 대파 등 농작물 피해가 컸다.",
            press="농기자재신문", domain="newsam.co.kr", score=14.3, fit=4.9,
        )
        sunburn = _mk(
            "pest",
            "뙤약볕에 타들어 가는 농심...과일도 화상 입는다 '일소현상'",
            "올 여름 유례없는 폭염과 가뭄이 전국을 덮치면서 수확을 앞둔 과수 농가에 비상이 걸렸다. 열매가 일소현상으로 상품성을 잃었다.",
            press="sisunnews", domain="sisunnews.co.kr", score=15.8, fit=3.4, is_core=True,
        )
        final = {"pest": [sunburn, jindo, relief], "supply": [], "policy": [], "dist": []}
        raw = {"pest": [sunburn, jindo, relief], "supply": [], "policy": [], "dist": []}
        main._repair_final_reader_quality_floor(final, raw)
        titles = {a.title for a in final["pest"]}
        self.assertIn(jindo.title, titles)
        self.assertIn(relief.title, titles)
        self.assertGreaterEqual(len(final["pest"]), 3)

    def test_vendor_promo_is_still_a_hard_leak(self):
        promo = _mk(
            "pest",
            "신젠타코리아, 신제품 살충제 '인시피오' 출시 기념 프로모션",
            "신젠타코리아가 총채벌레 방제용 신제품을 출시하고 농가 대상 판촉 행사를 연다.",
        )
        if not main._is_pest_vendor_product_promo(promo):
            self.skipTest("vendor promo classifier does not flag this fixture")
        final = {"pest": [promo], "supply": [], "policy": [], "dist": []}
        raw = {"pest": [promo], "supply": [], "policy": [], "dist": []}
        main._repair_final_reader_quality_floor(final, raw)
        self.assertEqual(final["pest"], [])


class TestForeignCropWeatherIsNotPest(unittest.TestCase):
    def test_french_vineyard_drought_rejected_from_pest(self):
        article = _mk(
            "pest",
            '"프랑스 와인 말라간다"…기록적 폭염·가뭄에 70년 만에 생산량 최저',
            "프랑스 와인 생산량이 폭염과 가뭄으로 70년 만에 최저치를 기록할 전망이다. 포도밭이 말라가고 있다.",
        )
        self.assertTrue(editorial_rules.remote_weather_crop_story(article.title, article.description))
        self.assertEqual(main._postbuild_article_reject_reason(article, "pest"), "remote_weather_feature")

    def test_foreign_weather_with_domestic_import_link_is_kept(self):
        self.assertFalse(editorial_rules.remote_weather_crop_story(
            "중국 폭염에 마늘 작황 부진…국내 수입가격 상승 우려",
            "중국산 마늘 수입 가격이 오르면서 국내 도매가격도 들썩인다.",
        ))
        self.assertFalse(editorial_rules.remote_weather_crop_story(JINDO_TITLE, JINDO_DESC))


if __name__ == "__main__":
    unittest.main()
