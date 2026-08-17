"""PR-1: 선정 가드와 평가 심판이 같은 테마 기준을 쓰는지, 기상 생육 리스크
기사가 pest 섹션에 실제로 진입하는지 검증한다.

배경: 2026-08 주간에 pest_theme_duplicate 가 5일 중 4일 발생해 최대 감점원이
됐는데, 실제로 감점된 카드는 씨스트선충·콩꼬투리혹파리처럼 서로 다른 기사였고
정작 같은 보도자료를 재가공한 참깨 기사 두 건은 그대로 통과했다. 원인은
'병해충'만 있으면 전부 general_pest 로 묶던 과대포괄 버킷이었다.
(reports/2026-08-16-weekly-score-improvement-plan.md)
"""
import unittest
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import crop_risk_vocab  # noqa: E402
import main  # noqa: E402
import report_eval  # noqa: E402


# 2026-08-10~14 지면에서 실제로 쓰인 pest 카드들(제목, 본문 일부).
LAST_WEEK_PEST_CARDS = (
    ("폭염 지속, 멜론 고온피해 예방 안내", "폭염이 이어지면서 멜론 시설재배지의 고온 피해 예방 관리를 당부했다."),
    ("충북농기원, 대추 과실 비대기 병해충 관리 강화 당부", "대추 과실 비대기에 병해충 관리와 방제를 강화해야 한다."),
    ("해충 꼬이고 햇볕에 타고…\"비 소식만 기다린다\"", "폭염과 가뭄이 길어지며 밭작물 해충 피해와 일소 피해가 늘고 있다."),
    ("전남광주농기원, 고온기 딸기 육묘관리 철저 당부", "고온기 딸기 육묘장 관리와 병해충 예찰을 당부했다."),
    ("대추 농가 '콩꼬투리혹파리·미국선녀벌레' 비상", "대추 재배지에서 콩꼬투리혹파리와 미국선녀벌레 피해가 확산돼 방제가 시급하다."),
    ("“씨스트선충 확산 막고 고랭지 배추 지켜라”", "고랭지 배추 재배지의 씨스트선충 확산을 막기 위해 예찰과 방제를 강화한다."),
)


def _make_pest_article(title: str, desc: str) -> "main.Article":
    link = "https://example.com/pest-card"
    return main.Article(
        section="pest",
        title=title,
        description=desc,
        link=link,
        originallink=link,
        pub_dt_kst=datetime.now(main.KST),
        domain="example.com",
        press="경남신문",
        norm_key="",
        title_key=main.norm_title_key(title),
        canon_url=link,
        topic="",
        score=30.0,
    )


class SharedPestThemeTests(unittest.TestCase):
    """가드(main)와 심판(report_eval)이 같은 버킷을 내야 한다."""

    def _guard_theme(self, title: str, desc: str) -> str:
        article = main.Article(
            section="pest",
            title=title,
            description=desc,
            link="https://example.com/pest-theme",
            originallink="https://example.com/pest-theme",
            pub_dt_kst=datetime.now(main.KST),
            domain="example.com",
            press="",
            norm_key="",
            title_key=main.norm_title_key(title),
            canon_url="https://example.com/pest-theme",
            topic="",
        )
        return main._pest_editorial_theme_key(article)

    def _judge_theme(self, title: str, desc: str) -> str:
        article = report_eval.SurfaceArticle(
            tag="div",
            surface=report_eval.BRIEFING_SURFACE,
            section="pest",
            title=title,
            href="https://example.com/pest-theme",
            article_id="pest-theme",
            domain="example.com",
        )
        return report_eval._pest_editorial_theme(article, desc)

    def test_guard_and_judge_agree_on_every_card(self) -> None:
        for title, desc in LAST_WEEK_PEST_CARDS:
            with self.subTest(title=title):
                self.assertEqual(self._guard_theme(title, desc), self._judge_theme(title, desc))

    def test_distinct_field_risks_do_not_collide(self) -> None:
        themes = [self._judge_theme(title, desc) for title, desc in LAST_WEEK_PEST_CARDS]
        self.assertTrue(all(themes), msg=str(themes))
        for theme in themes:
            self.assertLessEqual(
                themes.count(theme),
                2,
                msg=f"서로 다른 사안이 같은 버킷으로 묶였다: {theme} / {themes}",
            )

    def test_same_press_release_rework_shares_one_bucket(self) -> None:
        """같은 사안(농진청 참깨 방제)은 하나로 묶여야 dedup 이 가능하다."""
        first = self._judge_theme(
            "참깨 수확 앞두고 병해충 확산 우려…“발생 초기에 방제 해야”",
            "참깨 수확기를 앞두고 병해충 발생 초기 방제를 당부했다.",
        )
        second = self._judge_theme(
            "농진청, 참깨 수확 앞두고 병해충 적기 방제 당부",
            "농촌진흥청이 참깨 병해충 적기 방제를 당부했다.",
        )
        self.assertEqual(first, second)

    def test_named_pest_beats_generic_bucket(self) -> None:
        self.assertEqual(crop_risk_vocab.classify_pest_theme("씨스트선충 확산 막아라", "배추 병해충"), "nematode")
        self.assertEqual(crop_risk_vocab.classify_pest_theme("고추 응애 피해 우려", "방제 당부"), "mite")
        self.assertNotEqual(
            crop_risk_vocab.classify_pest_theme("씨스트선충 확산", "배추 병해충"),
            crop_risk_vocab.classify_pest_theme("콩꼬투리혹파리 비상", "대추 병해충"),
        )

    def test_short_crop_token_does_not_match_inside_a_longer_word(self) -> None:
        # '배'가 '배추'/'무'가 '무름병' 안에서 잡히면 엉뚱한 버킷이 된다.
        self.assertEqual(crop_risk_vocab.crop_bucket("배추 병해충 방제"), "배추")
        self.assertEqual(crop_risk_vocab.crop_bucket("배 과원 방제 당부"), "배")
        self.assertEqual(crop_risk_vocab.crop_bucket("무름병 잡는 미생물"), "")

    def test_legacy_theme_keys_are_preserved(self) -> None:
        cases = (
            ("고추역병 6월부터 발생…배수 관리 필요", "phytophthora"),
            ("영천시, 과수·산림지 돌발해충 합동방제", "outbreak_pest"),
            ("고온기 육묘장 병해충 확산 우려", "nursery_pest"),
            ("마늘·양파 여름철 토양 소독 당부", "soil_disinfection"),
        )
        for title, expected in cases:
            with self.subTest(title=title):
                self.assertEqual(self._judge_theme(title, f"{title} 병해충 방제 안내"), expected)


class WeatherRiskVocabTests(unittest.TestCase):
    """가뭄·폭염 기사가 pest 섹션에 들어오는지 (경남 가뭄 누락 재발 방지)."""

    @classmethod
    def setUpClass(cls) -> None:
        cls.conf = {section["key"]: section for section in main.SECTIONS}
        cls.now = datetime.now(main.KST)

    def _is_relevant_for_pest(self, title: str, desc: str, url: str) -> bool:
        dom = main.domain_of(url)
        press = main.normalize_press_label(main.press_name_from_url(url), url)
        return main.is_relevant(title, desc, dom, url, self.conf["pest"], press)

    def test_direct_injury_terms_count_as_pest_signal_on_their_own(self) -> None:
        for term in ("냉해", "고온피해", "일소", "우박", "습해"):
            with self.subTest(term=term):
                self.assertIn(term, main.PEST_WEATHER_TERMS)

    def test_bare_weather_event_needs_a_crop_damage_signal(self) -> None:
        """'폭염'·'가뭄'은 여름 물가·복지 기사에도 흔해 단독으로는 신호가 아니다."""
        for term in ("가뭄", "폭염", "한파" if "한파" in crop_risk_vocab.CROP_WEATHER_EVENT_TERMS else "장마"):
            with self.subTest(term=term):
                self.assertNotIn(term, main.PEST_WEATHER_TERMS)

        self.assertTrue(
            crop_risk_vocab.weather_event_damage_signal(
                "가뭄에 성주 참외 시들…고추 농사 직격탄",
                "가뭄으로 참외가 시들고 고추 생육이 부진하다.",
            )
        )
        self.assertFalse(
            crop_risk_vocab.weather_event_damage_signal(
                "40도 폭염에 시금치 한 달 새 152% 폭등",
                "폭염으로 채소 소매가격이 급등하며 밥상물가 부담이 커졌다.",
            )
        )

    def test_summer_price_story_stays_out_of_pest_section(self) -> None:
        title = "40도 폭염에 '히트플레이션' 현실화…시금치 한 달 새 152% 폭등"
        desc = "폭염으로 시금치 등 채소 소매가격이 급등하며 밥상물가 부담이 커졌다."
        self.assertFalse(self._is_relevant_for_pest(title, desc, "https://example.com/heatflation"))

    def test_drought_crop_damage_story_enters_pest_section(self) -> None:
        title = "경남 가뭄 확산…밭작물 시들고 과수 생육 피해 비상"
        desc = "경남 지역 가뭄이 길어지며 고추·참깨 등 밭작물이 시들고 과수 생육 피해가 커져 급수 대책과 관수 지원을 서두르고 있다."
        self.assertTrue(main.is_pest_story_focus_strong(title, desc))
        self.assertTrue(self._is_relevant_for_pest(title, desc, "https://example.com/drought-damage"))

    def test_drought_crop_damage_survives_the_post_build_audit(self) -> None:
        """유입만으로는 부족하다 — 발행 직전 감사까지 살아남아야 지면에 오른다."""
        cases = (
            (
                "경남 전역 가뭄 '비상'…단감·참외 말라가고 급수 대책 총력",
                "경남 전역 가뭄으로 단감과 참외 등 과수·채소가 말라가면서 농가가 관수와 급수 대책에 나섰다.",
            ),
            (
                "폭염·가뭄에 제주 당근 파종 지연···파종률 20%",
                "제주 당근 파종이 폭염과 가뭄으로 지연되면서 파종률이 20%에 그쳤다.",
            ),
        )
        for title, desc in cases:
            with self.subTest(title=title):
                url = "https://example.com/drought-audit"
                article = main.Article(
                    section="pest",
                    title=title,
                    description=desc,
                    link=url,
                    originallink=url,
                    pub_dt_kst=self.now,
                    domain="example.com",
                    press="연합뉴스",
                    norm_key="",
                    title_key=main.norm_title_key(title),
                    canon_url=url,
                    topic="",
                )
                reason = main._postbuild_article_reject_reason(article, "pest")
                self.assertNotIn(reason, main._HARD_FINAL_POSTBUILD_REJECT_REASONS, msg=reason)
                self.assertEqual(reason, "", msg=reason)

    def test_foreign_drought_aid_story_is_rejected(self) -> None:
        title = "가뭄 시달리는 과테말라···K-농업 '단비'"
        desc = "과테말라 건조지역에 한국 농업기술을 전수해 가뭄 대응 관수 시설을 지원했다."
        url = "https://example.com/guatemala"
        article = main.Article(
            section="pest",
            title=title,
            description=desc,
            link=url,
            originallink=url,
            pub_dt_kst=self.now,
            domain="example.com",
            press="연합뉴스",
            norm_key="",
            title_key=main.norm_title_key(title),
            canon_url=url,
            topic="",
        )
        self.assertNotEqual(main._postbuild_article_reject_reason(article, "pest"), "")

    def test_heat_welfare_campaign_stays_out_of_pest_section(self) -> None:
        title = "폭염 대비 무더위 쉼터 운영…온열질환 예방 캠페인"
        desc = "지자체가 폭염에 대비해 무더위 쉼터를 운영하고 생수 지원과 온열질환 예방 캠페인을 벌인다."
        article = main.Article(
            section="pest",
            title=title,
            description=desc,
            link="https://example.com/heat-welfare",
            originallink="https://example.com/heat-welfare",
            pub_dt_kst=self.now,
            domain="example.com",
            press="",
            norm_key="",
            title_key=main.norm_title_key(title),
            canon_url="https://example.com/heat-welfare",
            topic="",
        )
        self.assertTrue(main._is_pest_weather_disaster_noise(article))

    def test_supply_climate_gate_covers_drought_with_measured_output(self) -> None:
        self.assertTrue(
            main._is_supply_climate_output_context(
                "가뭄에 배추 생산량 뚝",
                "가뭄으로 배추 생산량이 전년 대비 20% 줄어 수급 불안이 커졌다.",
            )
        )

    def test_judge_accepts_weather_field_damage_as_core(self) -> None:
        article = report_eval.SurfaceArticle(
            tag="div",
            surface=report_eval.BRIEFING_SURFACE,
            section="pest",
            title="경남 가뭄 피해 확산…밭작물 고사 비상",
            href="https://example.com/drought-core",
            article_id="drought-core",
            domain="example.com",
            is_core=True,
        )
        body = "가뭄으로 밭작물이 고사하면서 농가 피해가 커져 급수 지원과 관수 대책을 추진한다."
        self.assertTrue(report_eval._is_priority_field_risk_core(article, body))

    def test_selection_gate_accepts_generic_headline_damage_wording(self) -> None:
        """헤드라인이 총칭 피해어만 써도 선발 게이트가 코어로 인정한다.

        실제 기상재해 헤드라인은 '가뭄 피해 확산', '폭염에 농가 비상'처럼 총칭을
        쓰는데, 구체 피해 양상(시들·낙과·급수) 어휘만 보면 이런 제목이 코어에서
        빠지고 report_eval 의 기상재해 분기와 기준이 어긋난다.
        """
        title = "경남 가뭄 피해 확산…농가 비상"
        desc = "가뭄이 이어지며 밭작물이 시들고 농가가 급수 대책에 나섰다. 재배지 피해가 커지고 있다."
        article = _make_pest_article(title, desc)

        self.assertTrue(main._headline_gate(article, "pest"), msg=title)

        surface = report_eval.SurfaceArticle(
            tag="div",
            surface=report_eval.BRIEFING_SURFACE,
            section="pest",
            title=title,
            href="https://example.com/generic-damage",
            article_id="generic-damage",
            domain="example.com",
            is_core=True,
        )
        self.assertTrue(report_eval._is_priority_field_risk_core(surface, desc))

    def test_every_managed_commodity_term_gets_a_crop_bucket(self) -> None:
        """COMMODITY_REGISTRY 의 품목 어휘는 모두 테마 버킷을 받아야 한다.

        crop_risk_vocab 는 report_eval 에서도 import 하므로 main 에 의존할 수 없어
        품목 어휘를 따로 들고 있다. 그래서 레지스트리에 품목/별칭이 추가돼도 이쪽이
        따라가지 못하면 서로 다른 품목 기사가 전부 general_pest 로 뭉쳐 중복 테마
        가드에 걸린다. 어휘가 어긋나면 여기서 바로 실패하게 한다.
        """
        unbucketed: list[tuple[str, str]] = []
        for item in main.COMMODITY_REGISTRY:
            topic = str(item.get("topic") or "")
            terms = {str(item.get("rep_term") or ""), topic}
            terms |= {str(term) for term in (item.get("aliases") or [])}
            terms |= {str(term) for term in (item.get("focus_terms") or [])}
            for term in sorted(t.strip() for t in terms if str(t).strip()):
                if " " in term or "(" in term:
                    continue  # 서술형 별칭('배 과일')은 버킷 토큰 대상이 아니다
                if not crop_risk_vocab.crop_bucket(crop_risk_vocab.normalize(f"{term} 병해충 확산")):
                    unbucketed.append((topic, term))
        self.assertEqual(unbucketed, [], msg=f"crop bucket 어휘 누락: {unbucketed}")

    def test_distinct_commodities_do_not_share_a_pest_theme(self) -> None:
        """서로 다른 관리품목 기사는 서로 다른 테마를 받아야 중복 가드에 안 걸린다."""
        themes = {
            title: crop_risk_vocab.classify_pest_theme(title)
            for title in ("피망 병해충 확산", "신고배 병해충 확산", "알밤 병해충 확산")
        }
        self.assertNotIn("general_pest", themes.values(), msg=str(themes))
        self.assertEqual(len(set(themes.values())), 3, msg=str(themes))

    def test_commodity_spelling_variants_share_one_theme(self) -> None:
        """같은 품목의 표기 변형은 한 버킷으로 모여 중복으로 잡혀야 한다."""
        for left, right in (
            ("신고배 병해충 확산", "나주배 병해충 확산"),
            ("샤인머스캣 병해충 확산", "샤인머스켓 병해충 확산"),
            ("주키니 병해충 확산", "쥬키니 병해충 확산"),
        ):
            self.assertEqual(
                crop_risk_vocab.classify_pest_theme(left),
                crop_risk_vocab.classify_pest_theme(right),
                msg=f"{left} vs {right}",
            )

    def test_boundary_protected_tokens_do_not_false_match(self) -> None:
        """다른 낱말에 들어간 품목 글자를 품목으로 오인하지 않는다."""
        for title in ("만감이 교차하는 수확철", "생화학 무기 협약 논의", "배수로 정비 사업"):
            self.assertEqual(crop_risk_vocab.crop_bucket(crop_risk_vocab.normalize(title)), "", msg=title)


if __name__ == "__main__":
    unittest.main()
