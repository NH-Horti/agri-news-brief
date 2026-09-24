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


REDHYANG_TITLE = "레드향 열과 피해 벌써 20%…올해도 되풀이"
REDHYANG_DESC = (
    "[KBS 제주] [앵커] 레드향 재배 농가들의 속을 터지게 하는 열과 피해가 올해도 어김없이 되풀이되고 있습니다. "
    "발생률은 벌써 20%를 넘어 예년과 비슷한 수준에 달했는데요. [리포트] 비닐하우스에서 재배 중인 만감류 감귤 품종 레드향. "
    "껍질이 쩍쩍 갈라진 채 바닥에 뒹굽니다. 이 농가는 전체 레드향 중 70% 정도가 열과 피해를 입었습니다. "
    "올해 레드향 열과 발생률은 지난 12일 기준 21.4%. 2024년 22.3%, 지난해 23.6%와 비슷한 수준입니다. "
    "[송상철/제주농업기술원 기술지원팀장 : \"재배 환경이 몇 가지라도 맞지 않으면 열과가 많이 발생하는 특성을 갖고 있는 품종입니다.\"] "
    "농가의 시름을 덜어줄 대책 마련이 시급해지고 있습니다. KBS 뉴스 고기욱입니다."
)


def _redhyang(section="supply"):
    return _mk(section, REDHYANG_TITLE, REDHYANG_DESC, press="KBS", domain="news.kbs.co.kr", score=39.4, fit=3.9)


class TestQuantifiedCropDamageReportIsNotPromoFiller(unittest.TestCase):
    """2026-09-22 과제 2: 레드향 열과 KBS 기사가 인터뷰이 직함('기술지원팀장')의 '지원' 한 글자로
    supply 코어에서 promotional_or_event_filler 로 강등되고, '열과'가 어느 pest 어휘에도 없어
    pest 후보도 되지 못했다."""

    def test_damage_rate_field_report_is_quantified_crop_damage(self):
        self.assertTrue(main._is_quantified_crop_damage_report(_redhyang()))

    def test_supply_promo_gate_exempts_quantified_damage_report(self):
        self.assertEqual(main._editorial_safe_core_demote_reason(_redhyang(), "supply"), "")
        self.assertEqual(main._postbuild_article_reject_reason(_redhyang(), "supply"), "")

    def test_event_title_with_damage_words_is_still_promo(self):
        article = _mk(
            "supply",
            "피해 농가 돕기 사과 판촉 행사 개최…20% 할인 판매",
            "우박 피해를 입은 농가를 돕기 위한 판촉 행사가 열렸다. 홍보 캠페인과 나눔 행사도 함께 진행됐다.",
        )
        self.assertFalse(main._is_quantified_crop_damage_report(article))
        self.assertEqual(main._editorial_safe_core_demote_reason(article, "supply"), "promotional_or_event_filler")

    def test_physiological_disorder_vocab_makes_pest_candidate(self):
        article = _redhyang()
        pest_conf = next(s for s in main.SECTIONS if s.get("key") == "pest")
        self.assertGreaterEqual(main._pest_weather_hits(article.title.lower()), 1)
        self.assertTrue(main._has_pest_or_growth_risk_signal(article.title, article.description))
        self.assertTrue(main.is_relevant(article.title, article.description, article.domain, article.link, pest_conf, article.press))
        self.assertTrue(main.is_pest_story_focus_strong(article.title, article.description))
        self.assertEqual(main._editorial_safe_core_demote_reason(article, "pest"), "")
        self.assertFalse(main._is_generic_pest_notice_tail(article))
        self.assertEqual(
            main._preferred_tail_block_reason(article, "pest", current_count=4, raw_count=11),
            "",
        )
        self.assertTrue(main._is_cross_day_pest_candidate(article))

    def test_time_adverb_with_particle_is_not_a_local_geo(self):
        # '올해도'가 [가-힣]{2,6}(군|시|구|도) 지역명 패턴에 걸려 pest 지역 공지 판정을 켰다.
        self.assertFalse(main._local_geo_match("레드향 열과 피해 벌써 20%…올해도 되풀이"))
        self.assertTrue(main._local_geo_match("영천시, 과수 농림지 돌발 해충 성충기 공동 방제"))

    def test_bounded_matching_ignores_words_containing_the_term(self):
        from crop_risk_vocab import classify_pest_theme, physiological_disorder_hits

        self.assertEqual(physiological_disorder_hits("농협 계열과 협력해 매장 진열과 판매를 늘렸다"), 0)
        self.assertEqual(physiological_disorder_hits("탈락과 합격 사이"), 0)
        # '열과 성을 다하다'(熱과 誠)는 관용구다.
        self.assertEqual(physiological_disorder_hits("조합원을 위해 열과 성을 다하겠다"), 0)
        self.assertEqual(physiological_disorder_hits("레드향 열과 피해, 낙과율 30%"), 2)
        self.assertEqual(main._pest_weather_hits("농협 계열과 협력"), 0)
        # 품목이 제목에 있으면 기존 품목 버킷 그대로, 없으면 general_pest 대신 생리장해 버킷.
        self.assertEqual(classify_pest_theme(REDHYANG_TITLE, REDHYANG_DESC), "crop_레드향")
        self.assertEqual(classify_pest_theme("열과 피해 확산…농가 시름", "병해충 방제와 함께 열과 대책이 필요하다"), "physio_cracking")
        self.assertEqual(classify_pest_theme("태풍에 낙과 속출", "낙과 피해가 크다"), "weather_storm")

    def test_evaluator_treats_physiological_damage_headline_as_field_risk_core(self):
        import report_eval

        article = report_eval.SurfaceArticle(
            tag="li", surface=report_eval.BRIEFING_SURFACE, section="pest", title=REDHYANG_TITLE,
            href="https://news.kbs.co.kr/x", article_id="x", domain="news.kbs.co.kr",
            summary="레드향 열과 발생률이 20%를 넘어 농가 피해가 반복되고 있다.", is_core=True,
        )
        self.assertTrue(report_eval._is_priority_field_risk_core(article, REDHYANG_DESC))


class TestGlossaryExplainerIsNotPestCore(unittest.TestCase):
    """과제 3: '[지식용어]' 용어 해설 카드는 pest 코어를 차지하지 못한다(tail 은 허용)."""

    def _sunburn(self):
        return _mk(
            "pest",
            "뙤약볕에 타들어 가는 농심...과일도 화상 입는다 '일소현상' [지식용어]",
            "올 여름 유례없는 폭염과 가뭄이 전국을 덮치면서 수확을 앞둔 과수 농가에 비상이 걸렸다. 열매가 일소현상으로 상품성을 잃었다.",
            press="sisunnews", domain="sisunnews.co.kr", score=15.8, fit=3.4, is_core=True,
        )

    def test_glossary_tag_is_core_only_demotion(self):
        article = self._sunburn()
        self.assertEqual(main._editorial_safe_core_demote_reason(article, "pest"), "pest_glossary_explainer_core")
        article.is_core = False
        # 코어 전용 사유는 tail 배치를 막지 않는다(약한 tail 판정기는 별도 축이라 고정).
        with patch.object(main, "_is_weak_pest_tail", return_value=False),                 patch.object(main, "_is_generic_pest_notice_tail", return_value=False):
            self.assertEqual(
                main._preferred_tail_block_reason(article, "pest", current_count=4, raw_count=11),
                "",
            )

    def test_plain_damage_headline_keeps_core_eligibility(self):
        article = _mk(
            "pest",
            "뙤약볕에 타들어 가는 농심...과일도 화상 입는다 '일소현상' 피해 확산",
            "폭염에 사과·배 일소 피해가 늘고 있다.",
            press="sisunnews", domain="sisunnews.co.kr",
        )
        self.assertEqual(main._editorial_safe_core_demote_reason(article, "pest"), "")


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
